from app.models import User 

def test_create_user(db_session):
    new_user = User(username="test_user")

    db_session.add(new_user)
    db_session.commit()
    
    user_in_db = db_session.query(User).filter_by(username="test_user").first()
    assert user_in_db is not None
    assert user_in_db.username == "test_user"