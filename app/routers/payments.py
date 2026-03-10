import razorpay
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import models
from app.core.database import get_db
from app.dependencies import razorpay_client

router = APIRouter(prefix="/payment", tags=["Payments"])

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

    order = db.query(models.Order).filter(
        models.Order.razorpay_order_id == razorpay_order_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.razorpay_payment_id = razorpay_payment_id
    order.payment_status = "completed"
    # leave order.status as "pending"; admin will confirm before completing

    # wallet is not affected here

    db.commit()

    return {"message": "Payment verified and order completed"}
