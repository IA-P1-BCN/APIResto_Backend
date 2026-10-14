from sqlalchemy.orm import Session

from app.models.model_social_account import SocialAccount


def get(db: Session, provider: str, provider_user_id: str) -> SocialAccount | None:
    return (
        db.query(SocialAccount)
        .filter(
            SocialAccount.provider == provider,
            SocialAccount.provider_user_id == provider_user_id,
        )
        .first()
    )


def add(db: Session, account: SocialAccount) -> SocialAccount:
    db.add(account)
    db.commit()
    db.refresh(account)
    return account
