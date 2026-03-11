from app.core import models, schemas
from app.core.database import get_db
from app.dependencies import razorpay_client, get_current_user

router = APIRouter(prefix="/payment", tags=["Payments"])

@router.post("/wallet/topup")
def initiate_wallet_topup(
    request: schemas.WalletTopUpRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    # 1. Create WalletTransaction record
    tx = models.WalletTransaction(
        user_id=current_user.id,
        amount=request.amount,
        status="pending"
    )
    db.add(tx)
    db.flush()

    # 2. Create Razorpay order
    amount_paise = int(request.amount * 100)
    try:
        rz_order = razorpay_client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"wallet_topup_{tx.id}",
        })
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Razorpay error: {str(e)}")

    # 3. Store Razorpay order ID
    tx.razorpay_order_id = rz_order.get("id")
    db.commit()
    db.refresh(tx)

    return {
        "transaction_id": tx.id,
        "razorpay_order": rz_order,
        "message": "Wallet top-up initiated"
    }

@router.post("/verify")
def verify_payment(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    db: Session = Depends(get_db),
):
    params_dict = {
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature,
    }

    try:
        if razorpay_client:
            razorpay_client.utility.verify_payment_signature(params_dict)
        else:
            raise HTTPException(status_code=500, detail="Razorpay is not configured")
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    # Check if this is a product order
    order = db.query(models.Order).filter(
        models.Order.razorpay_order_id == razorpay_order_id
    ).first()

    if order:
        order.razorpay_payment_id = razorpay_payment_id
        order.payment_status = "completed"
        db.commit()
        return {"message": "Order payment verified and completed"}

    # Check if this is a wallet top-up
    tx = db.query(models.WalletTransaction).filter(
        models.WalletTransaction.razorpay_order_id == razorpay_order_id
    ).first()

    if tx:
        if tx.status == "completed":
            return {"message": "Wallet already topped up"}
            
        tx.razorpay_payment_id = razorpay_payment_id
        tx.status = "completed"
        
        # Credit user's wallet
        user = db.query(models.User).filter(models.User.id == tx.user_id).first()
        if user:
            user.balance += tx.amount
        
        db.commit()
        return {"message": "Wallet topped up successfully", "new_balance": user.balance}

    raise HTTPException(status_code=404, detail="Transaction or Order not found")

