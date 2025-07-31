from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import List, Optional
import os

app = FastAPI(title="Wave Client Server", description="Mock server for Wave client integration testing")

DATABASE_URL = "sqlite:///./wave_client.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class WaveSession(Base):
    __tablename__ = "wave_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="active")

class WaveMessage(Base):
    __tablename__ = "wave_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    content = Column(Text)
    message_type = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

class SessionCreate(BaseModel):
    session_id: str

class MessageCreate(BaseModel):
    session_id: str
    content: str
    message_type: str = "text"

class SessionResponse(BaseModel):
    id: int
    session_id: str
    created_at: datetime
    status: str

class MessageResponse(BaseModel):
    id: int
    session_id: str
    content: str
    message_type: str
    timestamp: datetime

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    return {"message": "Wave Client Server", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.post("/sessions", response_model=SessionResponse)
async def create_session(session: SessionCreate):
    db = SessionLocal()
    try:
        existing_session = db.query(WaveSession).filter(WaveSession.session_id == session.session_id).first()
        if existing_session:
            raise HTTPException(status_code=400, detail="Session already exists")
        
        db_session = WaveSession(session_id=session.session_id)
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        return db_session
    finally:
        db.close()

@app.get("/sessions", response_model=List[SessionResponse])
async def list_sessions():
    db = SessionLocal()
    try:
        sessions = db.query(WaveSession).all()
        return sessions
    finally:
        db.close()

@app.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    db = SessionLocal()
    try:
        session = db.query(WaveSession).filter(WaveSession.session_id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    finally:
        db.close()

@app.post("/messages", response_model=MessageResponse)
async def create_message(message: MessageCreate):
    db = SessionLocal()
    try:
        session = db.query(WaveSession).filter(WaveSession.session_id == message.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        db_message = WaveMessage(
            session_id=message.session_id,
            content=message.content,
            message_type=message.message_type
        )
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        return db_message
    finally:
        db.close()

@app.get("/messages/{session_id}", response_model=List[MessageResponse])
async def get_messages(session_id: str):
    db = SessionLocal()
    try:
        session = db.query(WaveSession).filter(WaveSession.session_id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        messages = db.query(WaveMessage).filter(WaveMessage.session_id == session_id).all()
        return messages
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)