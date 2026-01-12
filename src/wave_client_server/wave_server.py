import json
import logging
import os
from datetime import datetime
from datetime import datetime as dt
from enum import Enum
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import (
    JSON as SQLAlchemyJSON,
)
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# Create logs directory
os.makedirs("logs", exist_ok=True)

# Configure logging
log_level = os.getenv("WAVE_DEBUG", "false").lower() in ("true", "1", "yes")
logging_level = logging.DEBUG if log_level else logging.INFO

# File handler for detailed logs
file_handler = logging.FileHandler(
    f"logs/wave_server_{dt.now().strftime('%Y%m%d_%H%M%S')}.log"
)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
file_handler.setFormatter(file_formatter)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging_level)
console_formatter = logging.Formatter("%(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)

# Configure root logger
logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Wave Server API",
    description="Wave Server API for Emacs client integration",
    version="0.2.0",
    openapi_url="/api/openapi.json",
    docs_url="/docs",
)

# CORS configuration - restrict origins in production
# Set ALLOWED_ORIGINS environment variable for production deployments
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:9898,http://localhost:3000,http://127.0.0.1:9898"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

DATABASE_URL = "sqlite:///./wave_server.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database Models
class Wave(Base):
    __tablename__ = "waves"

    id = Column(Integer, primary_key=True, index=True)
    wave_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    creator = Column(String)


class Wavelet(Base):
    __tablename__ = "wavelets"

    id = Column(Integer, primary_key=True, index=True)
    wave_id = Column(String, index=True)
    wavelet_id = Column(String, index=True)
    creator = Column(String)
    creation_time = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=0)
    history_hash = Column(String, default="")
    last_modified_time = Column(DateTime)
    participants = Column(SQLAlchemyJSON, default=list)
    docs = Column(SQLAlchemyJSON, default=dict)


class WaveletUpdate(Base):
    __tablename__ = "wavelet_updates"

    id = Column(Integer, primary_key=True, index=True)
    wave_id = Column(String, index=True)
    wavelet_id = Column(String, index=True)
    channel_id = Column(Integer)
    update_data = Column(SQLAlchemyJSON)
    timestamp = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


# Pydantic Models
class InboxItem(BaseModel):
    id: str
    digest: str
    unread: int = 0
    creator: str


class WaveletName(BaseModel):
    waveId: str = Field(alias="wave_id")
    waveletId: str = Field(alias="wavelet_id")

    class Config:
        populate_by_name = True


class Version(BaseModel):
    version: int
    historyHash: str = Field(alias="history_hash")

    class Config:
        populate_by_name = True


class Document(BaseModel):
    docId: str = Field(alias="doc_id")
    contributors: list[str] = []
    lastModifiedVersion: int | None = Field(None, alias="last_modified_version")
    lastModifiedTime: int | None = Field(None, alias="last_modified_time")
    content: list[str | dict[str, Any]] = []

    class Config:
        populate_by_name = True


class WaveletResponse(BaseModel):
    waveletName: WaveletName = Field(alias="wavelet_name")
    creator: str
    creationTime: int | None = Field(None, alias="creation_time")
    version: Version
    lastModifiedTime: int | None = Field(None, alias="last_modified_time")
    participants: list[str] = []
    docs: dict[str, Document] = {}

    class Config:
        populate_by_name = True


class OperationType(str, Enum):
    ADD_PARTICIPANT = "addParticipant"
    REMOVE_PARTICIPANT = "removeParticipant"
    DOCUMENT_OP = "documentOp"
    NO_OP = "noOp"


class Operation(BaseModel):
    type: OperationType
    participant: str | None = None
    docOp: dict[str, Any] | None = Field(None, alias="doc_op")

    class Config:
        populate_by_name = True


class Delta(BaseModel):
    author: str
    operations: list[Operation]


class DeltaSubmission(BaseModel):
    waveletName: WaveletName = Field(alias="wavelet_name")
    delta: Delta

    class Config:
        populate_by_name = True


class SubmitResponse(BaseModel):
    success: bool
    version: Version | None = None


class WebSocketMessageType(str, Enum):
    PROTOCOL_OPEN_REQUEST = "ProtocolOpenRequest"
    PROTOCOL_SUBMIT_REQUEST = "ProtocolSubmitRequest"
    PROTOCOL_WAVELET_UPDATE = "ProtocolWaveletUpdate"


class WebSocketMessage(BaseModel):
    version: int = 0
    sequenceNumber: int = Field(alias="sequence_number")
    messageType: WebSocketMessageType = Field(alias="message_type")
    messageJson: str = Field(alias="message_json")

    class Config:
        populate_by_name = True


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
        self.channel_callbacks: dict[int, str] = {}
        self.wave_channels: dict[str, int] = {}
        self.channel_counter = 0

    async def connect(self, websocket: WebSocket, client_id: str):
        logger.info(f"WebSocket connection attempt from client: {client_id}")
        await websocket.accept()
        logger.info(f"WebSocket connection accepted for client: {client_id}")
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)
        logger.debug(f"Active connections: {list(self.active_connections.keys())}")

    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            for connection in self.active_connections[client_id]:
                await connection.send_text(message)

    async def broadcast(self, message: str):
        for connections in self.active_connections.values():
            for connection in connections:
                await connection.send_text(message)

    def get_channel_number(self, wave_id: str) -> int:
        if wave_id not in self.wave_channels:
            self.channel_counter += 1
            self.wave_channels[wave_id] = self.channel_counter
            self.channel_callbacks[self.channel_counter] = wave_id
        return self.wave_channels[wave_id]


manager = ConnectionManager()


# Initialize with demo data
def init_demo_data(db: Session):
    # Check if already initialized
    if db.query(Wave).filter(Wave.wave_id == "indexwave!indexwave").first():
        return

    # Create index wave
    index_wave = Wave(wave_id="indexwave!indexwave", creator="system@localhost")
    db.add(index_wave)

    # Create index wavelet
    index_wavelet = Wavelet(
        wave_id="indexwave!indexwave",
        wavelet_id="indexwave!indexwave",
        creator="system@localhost",
        version=1,
        participants=["system@localhost"],
        docs={
            "main": {
                "docId": "main",
                "contributors": ["system@localhost"],
                "content": ["Welcome to Wave Server!"],
            }
        },
    )
    db.add(index_wavelet)
    db.commit()


# Middleware for request logging
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    logger.debug(f"Headers: {dict(request.headers)}")

    # Log request body for POST/PUT
    if request.method in ["POST", "PUT"]:
        body = await request.body()
        logger.debug(f"Request body: {body.decode('utf-8') if body else 'empty'}")
        # Recreate request with body
        from starlette.requests import Request

        request = Request(
            request.scope, receive=lambda: {"type": "http.request", "body": body}
        )

    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response


# API Endpoints
@app.get("/")
async def root():
    logger.debug("Root endpoint accessed")
    return {"message": "Wave Server API", "status": "running", "version": "0.2.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.debug("Health check accessed")
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/inbox", response_model=list[InboxItem])
async def get_inbox(db: Session = Depends(get_db)):
    logger.info("GET /api/inbox - Fetching inbox")
    init_demo_data(db)

    # Get all wavelets from indexwave (inbox)
    wavelets = db.query(Wavelet).all()
    logger.debug(f"Found {len(wavelets)} wavelets in database")
    inbox_items = []

    for wavelet in wavelets:
        docs = wavelet.docs or {}
        digest = ""
        if "digest" in docs:
            digest = " ".join(str(item) for item in docs["digest"].get("content", []))
        elif "main" in docs:
            digest = " ".join(str(item) for item in docs["main"].get("content", []))[
                :100
            ]

        inbox_items.append(
            InboxItem(
                id=wavelet.wavelet_id,
                digest=digest,
                unread=0,
                creator=wavelet.creator or "unknown@localhost",
            )
        )

    return inbox_items


@app.get("/api/waves/{wave_id}", response_model=list[WaveletResponse])
async def get_wave(wave_id: str, db: Session = Depends(get_db)):
    logger.info(f"GET /api/waves/{wave_id} - Fetching wave")
    wavelets = db.query(Wavelet).filter(Wavelet.wave_id == wave_id).all()
    logger.debug(f"Found {len(wavelets)} wavelets for wave {wave_id}")
    if not wavelets:
        raise HTTPException(status_code=404, detail="Wave not found")

    responses = []
    for wavelet in wavelets:
        docs_dict = {}
        if wavelet.docs:
            for doc_id, doc_data in wavelet.docs.items():
                # Handle case where doc_data might not be a dict
                if isinstance(doc_data, dict):
                    docs_dict[doc_id] = Document(
                        doc_id=doc_id,
                        contributors=doc_data.get("contributors", []),
                        last_modified_version=doc_data.get("lastModifiedVersion"),
                        last_modified_time=doc_data.get("lastModifiedTime"),
                        content=doc_data.get("content", []),
                    )
                else:
                    # doc_data is a primitive or list, wrap it as content
                    docs_dict[doc_id] = Document(
                        doc_id=doc_id,
                        contributors=[],
                        content=[doc_data]
                        if not isinstance(doc_data, list)
                        else doc_data,
                    )

        responses.append(
            WaveletResponse(
                wavelet_name=WaveletName(
                    wave_id=wavelet.wave_id, wavelet_id=wavelet.wavelet_id
                ),
                creator=wavelet.creator,
                creation_time=int(wavelet.creation_time.timestamp())
                if wavelet.creation_time
                else None,
                version=Version(
                    version=wavelet.version, history_hash=wavelet.history_hash or ""
                ),
                last_modified_time=int(wavelet.last_modified_time.timestamp())
                if wavelet.last_modified_time
                else None,
                participants=wavelet.participants or [],
                docs=docs_dict,
            )
        )

    return responses


@app.post("/api/waves/{wave_id}/submit", response_model=SubmitResponse)
async def submit_delta(
    wave_id: str, submission: DeltaSubmission, db: Session = Depends(get_db)
):
    logger.info(f"POST /api/waves/{wave_id}/submit - Submitting delta")
    logger.debug(f"Delta submission: {submission.dict()}")
    wavelet = (
        db.query(Wavelet)
        .filter(
            Wavelet.wave_id == wave_id,
            Wavelet.wavelet_id == submission.waveletName.waveletId,
        )
        .first()
    )

    if not wavelet:
        # Create new wavelet
        wavelet = Wavelet(
            wave_id=wave_id,
            wavelet_id=submission.waveletName.waveletId,
            creator=submission.delta.author,
            participants=[submission.delta.author],
            docs={},
        )
        db.add(wavelet)

    # Process operations
    for op in submission.delta.operations:
        if op.type == OperationType.ADD_PARTICIPANT and op.participant:
            if op.participant not in wavelet.participants:
                wavelet.participants = wavelet.participants + [op.participant]
        elif op.type == OperationType.REMOVE_PARTICIPANT and op.participant:
            wavelet.participants = [
                p for p in wavelet.participants if p != op.participant
            ]
        elif op.type == OperationType.DOCUMENT_OP and op.doc_op:
            # Handle document operations
            doc_id = op.doc_op.get("docId", "main")
            if doc_id not in wavelet.docs:
                wavelet.docs[doc_id] = {
                    "docId": doc_id,
                    "contributors": [],
                    "content": [],
                }
            wavelet.docs[doc_id]["contributors"] = list(
                set(
                    wavelet.docs[doc_id].get("contributors", [])
                    + [submission.delta.author]
                )
            )

    wavelet.version += 1
    wavelet.last_modified_time = datetime.utcnow()

    db.commit()
    db.refresh(wavelet)

    # Broadcast update via WebSocket
    update_message = {
        "version": 0,
        "sequenceNumber": manager.get_channel_number(wave_id),
        "messageType": "ProtocolWaveletUpdate",
        "messageJson": json.dumps(
            {
                "1": f"wave://localhost/{wave_id}/{submission.waveletName.waveletId}",
                "2": [],  # deltas
                "4": {"1": wavelet.version, "2": wavelet.history_hash or ""},
            }
        ),
    }
    await manager.broadcast(json.dumps(update_message))

    return SubmitResponse(
        success=True,
        version=Version(
            version=wavelet.version, history_hash=wavelet.history_hash or ""
        ),
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str = "default"):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Raw WebSocket data received: {data}")
            message = json.loads(data)

            logger.info(f"WebSocket message type: {message.get('messageType')}")
            logger.debug(f"Full WebSocket message: {json.dumps(message, indent=2)}")

            # Handle different message types
            if message.get("messageType") == "ProtocolOpenRequest":
                # Parse the message JSON
                msg_data = json.loads(message.get("messageJson", "{}"))
                wave_id = msg_data.get("2", "indexwave!indexwave")

                # Send initial wavelet update
                db = SessionLocal()
                try:
                    wavelets = (
                        db.query(Wavelet).filter(Wavelet.wave_id == wave_id).all()
                    )
                    for wavelet in wavelets:
                        update = {
                            "version": 0,
                            "sequenceNumber": message.get("sequenceNumber", 1),
                            "messageType": "ProtocolWaveletUpdate",
                            "messageJson": json.dumps(
                                {
                                    "1": f"wave://localhost/{wavelet.wave_id}/{wavelet.wavelet_id}",
                                    "2": [],  # deltas
                                    "4": {
                                        "1": wavelet.version,
                                        "2": wavelet.history_hash or "",
                                    },
                                }
                            ),
                        }
                        await websocket.send_text(json.dumps(update))
                finally:
                    db.close()

            elif message.get("messageType") == "ProtocolSubmitRequest":
                # Handle submit requests
                msg_data = json.loads(message.get("messageJson", "{}"))
                logger.info(f"Submit request: {msg_data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket, client_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9898)
