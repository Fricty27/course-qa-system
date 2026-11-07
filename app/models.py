from pydantic import BaseModel


class QueryRequest(BaseModel):
    course_id: str
    question: str
    history: list[dict] = []



class UploadResponse(BaseModel):
    status: str
    chunks: int
    message: str


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str


class CourseCreate(BaseModel):
    name: str
    course_key: str


class CourseRename(BaseModel):
    name: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str


class ProfileUpdate(BaseModel):
    avatar: str | None = None
    nickname: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class MessageCreate(BaseModel):
    receiver_id: int
    content: str
    course_key: str | None = None


class NoteCreate(BaseModel):
    course_key: str = ''
    doc_name: str = 'standalone'
    page_num: int = 0
    title: str = ''
    content: str
    is_public: bool = False
    is_ai: bool = False


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    is_public: bool | None = None
    course_key: str | None = None


class NoteCommentCreate(BaseModel):
    content: str


class BasicInfoUpdate(BaseModel):
    gender: str | None = None
    phone: str | None = None


class PinRequest(BaseModel):
    message_id: int


class GroupMessageCreate(BaseModel):
    content: str


class ScheduleCreate(BaseModel):
    date: str
    title: str
    content: str = ""


class ScheduleUpdate(BaseModel):
    title: str
    content: str = ""


class PublicScheduleCreate(BaseModel):
    date: str
    title: str
    content: str = ""
    course_key: str
