import sqlite3
import hashlib
import os
import uuid
from datetime import datetime, timedelta

DB_PATH = "data/courseqa.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    os.makedirs("data", exist_ok=True)
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    UNIQUE NOT NULL,
                password_hash TEXT    NOT NULL,
                role          TEXT    NOT NULL CHECK(role IN ('teacher','student')),
                avatar        TEXT,
                nickname      TEXT,
                created_at    TEXT    DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS courses (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL,
                course_key TEXT    UNIQUE NOT NULL,
                teacher_id INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT    DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS course_members (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL REFERENCES users(id),
                course_key TEXT    NOT NULL,
                joined_at  TEXT    DEFAULT (datetime('now')),
                UNIQUE(student_id, course_key)
            );
            CREATE TABLE IF NOT EXISTS question_logs (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id          INTEGER REFERENCES users(id),
                student_name        TEXT,
                course_key          TEXT NOT NULL,
                course_name         TEXT,
                question            TEXT NOT NULL,
                answer              TEXT,
                created_at          TEXT DEFAULT (datetime('now')),
                deleted_by_teacher  INTEGER DEFAULT 0,
                deleted_by_student  INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                expires_at TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id   INTEGER NOT NULL REFERENCES users(id),
                receiver_id INTEGER NOT NULL REFERENCES users(id),
                course_key  TEXT,
                content     TEXT NOT NULL,
                is_read     INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS notes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL REFERENCES users(id),
                course_key TEXT NOT NULL,
                doc_name   TEXT NOT NULL,
                page_num   INTEGER NOT NULL,
                title      TEXT DEFAULT '',
                content    TEXT NOT NULL,
                is_public  INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS note_comments (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id    INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
                teacher_id INTEGER NOT NULL REFERENCES users(id),
                content    TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS groups (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                course_key TEXT UNIQUE NOT NULL,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS group_members (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id     INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                user_id      INTEGER NOT NULL REFERENCES users(id),
                last_read_at TEXT    DEFAULT (datetime('now','localtime')),
                joined_at    TEXT    DEFAULT (datetime('now','localtime')),
                UNIQUE(group_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS group_messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id   INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                sender_id  INTEGER NOT NULL REFERENCES users(id),
                content    TEXT    NOT NULL,
                created_at TEXT    DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS conversation_pins (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                other_id   INTEGER NOT NULL REFERENCES users(id),
                message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                pinned_at  TEXT    DEFAULT (datetime('now','localtime')),
                UNIQUE(user_id, other_id)
            );
            CREATE TABLE IF NOT EXISTS group_pins (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id   INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                message_id INTEGER NOT NULL REFERENCES group_messages(id) ON DELETE CASCADE,
                pinned_by  INTEGER NOT NULL REFERENCES users(id),
                pinned_at  TEXT    DEFAULT (datetime('now','localtime')),
                UNIQUE(group_id, message_id)
            );
            CREATE TABLE IF NOT EXISTS schedules (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                date       TEXT NOT NULL,
                title      TEXT NOT NULL,
                content    TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS public_schedules (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id   INTEGER NOT NULL REFERENCES users(id),
                course_key   TEXT NOT NULL,
                date         TEXT NOT NULL,
                title        TEXT NOT NULL,
                content      TEXT DEFAULT '',
                cancelled    INTEGER DEFAULT 0,
                created_at   TEXT DEFAULT (datetime('now','localtime')),
                cancelled_at TEXT DEFAULT NULL
            );
            CREATE TABLE IF NOT EXISTS public_schedule_reads (
                user_id     INTEGER NOT NULL REFERENCES users(id),
                schedule_id INTEGER NOT NULL REFERENCES public_schedules(id) ON DELETE CASCADE,
                read_at     TEXT DEFAULT (datetime('now','localtime')),
                PRIMARY KEY (user_id, schedule_id)
            );
            CREATE TABLE IF NOT EXISTS schedule_notifications (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                schedule_id INTEGER NOT NULL REFERENCES public_schedules(id) ON DELETE CASCADE,
                type        TEXT NOT NULL,
                shown       INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now','localtime')),
                UNIQUE(user_id, schedule_id, type)
            );
        """)
    # 迁移已有数据库：添加新列
    with _conn() as conn:
        for tbl_col in (
            ("users", "avatar TEXT"),
            ("users", "nickname TEXT"),
            ("users", "gender TEXT"),
            ("users", "phone TEXT"),
            ("question_logs", "deleted_by_teacher INTEGER DEFAULT 0"),
            ("question_logs", "deleted_by_student INTEGER DEFAULT 0"),
            ("notes", "title TEXT DEFAULT ''"),
            ("notes", "is_ai INTEGER DEFAULT 0"),
        ):
            try:
                conn.execute(f"ALTER TABLE {tbl_col[0]} ADD COLUMN {tbl_col[1]}")
            except Exception:
                pass  # 列已存在
    # 为已有课程补建群组（幂等）
    with _conn() as conn:
        courses = conn.execute("SELECT id, name, course_key, teacher_id FROM courses").fetchall()
        for c in courses:
            try:
                conn.execute("INSERT OR IGNORE INTO groups (name, course_key) VALUES (?,?)", (c["name"], c["course_key"]))
            except Exception:
                pass
            try:
                g = conn.execute("SELECT id FROM groups WHERE course_key=?", (c["course_key"],)).fetchone()
                if g:
                    gid = g["id"]
                    conn.execute("INSERT OR IGNORE INTO group_members (group_id, user_id) VALUES (?,?)", (gid, c["teacher_id"]))
                    members = conn.execute("SELECT student_id FROM course_members WHERE course_key=?", (c["course_key"],)).fetchall()
                    for m in members:
                        conn.execute("INSERT OR IGNORE INTO group_members (group_id, user_id) VALUES (?,?)", (gid, m["student_id"]))
            except Exception:
                pass
    print("✅ 数据库初始化完成")


# ── 密码 ──────────────────────────────────────────────────────────────────────

def _hash_password(plain: str) -> str:
    salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 100_000)
    return f"{salt}${dk.hex()}"


def _verify_password(plain: str, stored: str) -> bool:
    try:
        salt, dk_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 100_000)
        return dk.hex() == dk_hex
    except Exception:
        return False


# ── 用户 ──────────────────────────────────────────────────────────────────────

def get_user_by_username(username: str) -> sqlite3.Row | None:
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()


def create_user(username: str, password: str, role: str) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
            (username, _hash_password(password), role),
        )
        return cur.lastrowid


def verify_password(plain: str, stored_hash: str) -> bool:
    return _verify_password(plain, stored_hash)


def change_password(user_id: int, new_password: str) -> None:
    with _conn() as conn:
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (_hash_password(new_password), user_id))


def delete_user(user_id: int, role: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        if role == "teacher":
            course_keys = [r["course_key"] for r in conn.execute(
                "SELECT course_key FROM courses WHERE teacher_id=?", (user_id,)
            ).fetchall()]
            for key in course_keys:
                conn.execute("DELETE FROM course_members WHERE course_key=?", (key,))
            conn.execute("DELETE FROM courses WHERE teacher_id=?", (user_id,))
        else:
            conn.execute("DELETE FROM course_members WHERE student_id=?", (user_id,))
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))


def update_user_profile(user_id: int, avatar: str | None, nickname: str | None) -> None:
    sets = ['nickname=?']
    params = [nickname]
    if avatar is not None:
        sets.append('avatar=?')
        params.append(avatar)
    params.append(user_id)
    with _conn() as conn:
        conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=?", params)


def update_user_basic_info(user_id: int, gender: str | None, phone: str | None) -> None:
    with _conn() as conn:
        conn.execute("UPDATE users SET gender=?, phone=? WHERE id=?", (gender, phone, user_id))


# ── Session ───────────────────────────────────────────────────────────────────

def create_session(user_id: int) -> str:
    token = str(uuid.uuid4())
    now = datetime.utcnow()
    now_iso = now.isoformat()
    expires_at = (now + timedelta(hours=24)).isoformat()
    with _conn() as conn:
        conn.execute("DELETE FROM sessions WHERE user_id=? AND expires_at < ?", (user_id, now_iso))
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?,?,?)",
            (token, user_id, expires_at),
        )
    return token


def get_user_by_token(token: str) -> sqlite3.Row | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT s.user_id, s.expires_at, u.username, u.role, u.id, u.avatar, u.nickname, u.gender, u.phone "
            "FROM sessions s JOIN users u ON s.user_id = u.id "
            "WHERE s.token = ?",
            (token,),
        ).fetchone()
    if row is None:
        return None
    now = datetime.utcnow()
    if datetime.fromisoformat(row["expires_at"]) < now:
        with _conn() as conn:
            conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now.isoformat(),))
        return None
    return row


# ── 课程 ──────────────────────────────────────────────────────────────────────

def create_course(name: str, course_key: str, teacher_id: int) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO courses (name, course_key, teacher_id) VALUES (?,?,?)",
            (name, course_key, teacher_id),
        )
        return cur.lastrowid


def get_courses_by_teacher(teacher_id: int) -> list:
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM courses WHERE teacher_id = ? ORDER BY created_at DESC",
            (teacher_id,),
        ).fetchall()


def get_course_by_key(course_key: str) -> sqlite3.Row | None:
    with _conn() as conn:
        return conn.execute(
            "SELECT c.*, u.username as teacher_username, u.nickname as teacher_nickname "
            "FROM courses c JOIN users u ON u.id = c.teacher_id "
            "WHERE c.course_key = ?", (course_key,)
        ).fetchone()


def update_course_name(course_key: str, teacher_id: int, new_name: str) -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE courses SET name=? WHERE course_key=? AND teacher_id=?",
            (new_name, course_key, teacher_id),
        )
        return cur.rowcount > 0


def delete_course(course_key: str, teacher_id: int) -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "DELETE FROM courses WHERE course_key=? AND teacher_id=?",
            (course_key, teacher_id),
        )
        if cur.rowcount == 0:
            return False
        conn.execute("DELETE FROM course_members WHERE course_key=?", (course_key,))
        return True


# ── 课程成员 ──────────────────────────────────────────────────────────────────

def add_course_member(student_id: int, course_key: str) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO course_members (student_id, course_key) VALUES (?,?)",
            (student_id, course_key),
        )


def get_course_members(course_key: str) -> list:
    with _conn() as conn:
        return conn.execute(
            "SELECT u.id, u.username, u.avatar, u.nickname, cm.joined_at "
            "FROM course_members cm "
            "JOIN users u ON cm.student_id = u.id "
            "WHERE cm.course_key = ? "
            "ORDER BY cm.joined_at ASC",
            (course_key,),
        ).fetchall()


def get_student_courses(student_id: int) -> list:
    with _conn() as conn:
        return conn.execute(
            "SELECT c.course_key, c.name, cm.joined_at "
            "FROM course_members cm "
            "JOIN courses c ON cm.course_key = c.course_key "
            "WHERE cm.student_id = ? "
            "ORDER BY cm.joined_at DESC",
            (student_id,),
        ).fetchall()


# ── 提问日志 ──────────────────────────────────────────────────────────────────

def log_question(
    student_id: int | None,
    student_name: str,
    course_key: str,
    course_name: str,
    question: str,
    answer: str,
):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO question_logs "
            "(student_id, student_name, course_key, course_name, question, answer) "
            "VALUES (?,?,?,?,?,?)",
            (student_id, student_name, course_key, course_name, question, answer),
        )


def delete_question_log(log_id: int, user_id: int, role: str) -> bool:
    with _conn() as conn:
        if role == "teacher":
            cur = conn.execute(
                "UPDATE question_logs SET deleted_by_teacher=1 WHERE id=? AND course_key IN "
                "(SELECT course_key FROM courses WHERE teacher_id=?)",
                (log_id, user_id),
            )
        else:
            cur = conn.execute(
                "UPDATE question_logs SET deleted_by_student=1 WHERE id=? AND student_id=?",
                (log_id, user_id),
            )
        if cur.rowcount == 0:
            return False
        row = conn.execute(
            "SELECT deleted_by_teacher, deleted_by_student FROM question_logs WHERE id=?",
            (log_id,),
        ).fetchone()
        if row and row["deleted_by_teacher"] == 1 and row["deleted_by_student"] == 1:
            conn.execute("DELETE FROM question_logs WHERE id=?", (log_id,))
        return True


def get_student_question_logs(course_key: str, student_id: int) -> list:
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM question_logs WHERE course_key=? AND student_id=? AND deleted_by_student=0 ORDER BY created_at DESC",
            (course_key, student_id),
        ).fetchall()


def get_question_logs(course_key: str, teacher_id: int) -> list:
    with _conn() as conn:
        course = conn.execute(
            "SELECT id FROM courses WHERE course_key=? AND teacher_id=?",
            (course_key, teacher_id),
        ).fetchone()
        if course is None:
            return []
        return conn.execute(
            "SELECT * FROM question_logs WHERE course_key=? AND deleted_by_teacher=0 ORDER BY created_at DESC",
            (course_key,),
        ).fetchall()


# ── 私信 ──────────────────────────────────────────────────────────────────────

def send_message(sender_id: int, receiver_id: int, content: str, course_key: str | None = None) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO messages (sender_id, receiver_id, course_key, content) VALUES (?,?,?,?)",
            (sender_id, receiver_id, course_key, content),
        )
        return cur.lastrowid


def get_conversations(user_id: int) -> list:
    with _conn() as conn:
        return conn.execute("""
            SELECT
                u.id as other_id,
                u.username as other_username,
                u.nickname as other_nickname,
                u.avatar as other_avatar,
                u.role as other_role,
                sub.last_at,
                sub.unread,
                (SELECT m2.content FROM messages m2
                 WHERE (m2.sender_id = ? AND m2.receiver_id = u.id)
                    OR (m2.sender_id = u.id AND m2.receiver_id = ?)
                 ORDER BY m2.created_at DESC LIMIT 1) as last_content
            FROM (
                SELECT
                    CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END as other_id,
                    MAX(created_at) as last_at,
                    SUM(CASE WHEN receiver_id = ? AND is_read = 0 THEN 1 ELSE 0 END) as unread
                FROM messages
                WHERE sender_id = ? OR receiver_id = ?
                GROUP BY CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END
            ) sub
            JOIN users u ON u.id = sub.other_id
            ORDER BY sub.last_at DESC
        """, (user_id, user_id, user_id, user_id, user_id, user_id, user_id)).fetchall()


def get_conversation_messages(user_id: int, other_user_id: int) -> list:
    with _conn() as conn:
        rows = conn.execute("""
            SELECT m.id, m.sender_id, m.receiver_id, m.content, m.is_read, m.created_at,
                   s.username as sender_name, s.nickname as sender_nickname,
                   s.avatar as sender_avatar, s.role as sender_role
            FROM messages m
            JOIN users s ON s.id = m.sender_id
            WHERE (m.sender_id = ? AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = ?)
            ORDER BY m.created_at ASC
        """, (user_id, other_user_id, other_user_id, user_id)).fetchall()
        conn.execute(
            "UPDATE messages SET is_read=1 WHERE sender_id=? AND receiver_id=? AND is_read=0",
            (other_user_id, user_id),
        )
        return rows


def get_unread_count(user_id: int) -> int:
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE receiver_id=? AND is_read=0",
            (user_id,),
        ).fetchone()
        return row["cnt"] if row else 0


# ── 学生笔记 ──────────────────────────────────────────────────────────────────

def create_note(student_id: int, course_key: str, doc_name: str, page_num: int, content: str, is_public: bool, title: str = '', is_ai: bool = False) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO notes (student_id, course_key, doc_name, page_num, title, content, is_public, is_ai) VALUES (?,?,?,?,?,?,?,?)",
            (student_id, course_key, doc_name, page_num, title, content, 1 if is_public else 0, 1 if is_ai else 0),
        )
        return cur.lastrowid


def get_student_notes(student_id: int, course_key: str | None = None) -> list:
    with _conn() as conn:
        if course_key:
            return conn.execute(
                "SELECT * FROM notes WHERE student_id=? AND course_key=? ORDER BY created_at DESC",
                (student_id, course_key),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM notes WHERE student_id=? ORDER BY created_at DESC",
            (student_id,),
        ).fetchall()


def update_note(note_id: int, student_id: int, title: str | None = None, content: str | None = None, is_public: bool | None = None, course_key: str | None = None) -> bool:
    updates, values = [], []
    if title is not None:
        updates.append("title=?"); values.append(title)
    if content is not None:
        updates.append("content=?"); values.append(content)
    if is_public is not None:
        updates.append("is_public=?"); values.append(1 if is_public else 0)
    if course_key is not None:
        updates.append("course_key=?"); values.append(course_key)
    if not updates:
        return True
    values.extend([note_id, student_id])
    with _conn() as conn:
        cur = conn.execute(
            f"UPDATE notes SET {', '.join(updates)} WHERE id=? AND student_id=?", values
        )
        return cur.rowcount > 0


def delete_note(note_id: int, student_id: int) -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "DELETE FROM notes WHERE id=? AND student_id=?",
            (note_id, student_id),
        )
        return cur.rowcount > 0


def get_public_notes_for_teacher(teacher_id: int) -> list:
    with _conn() as conn:
        return conn.execute("""
            SELECT n.*, u.username as student_name, u.avatar as student_avatar, u.nickname as student_nickname
            FROM notes n
            JOIN users u ON u.id = n.student_id
            WHERE n.is_public = 1 AND n.course_key IN (
                SELECT course_key FROM courses WHERE teacher_id = ?
            )
            ORDER BY n.created_at DESC
        """, (teacher_id,)).fetchall()


def add_note_comment(note_id: int, teacher_id: int, content: str) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO note_comments (note_id, teacher_id, content) VALUES (?,?,?)",
            (note_id, teacher_id, content),
        )
        return cur.lastrowid


def get_note_comments(note_id: int) -> list:
    with _conn() as conn:
        return conn.execute("""
            SELECT nc.*, u.username as teacher_name, u.avatar as teacher_avatar, u.nickname as teacher_nickname
            FROM note_comments nc
            JOIN users u ON u.id = nc.teacher_id
            WHERE nc.note_id = ?
            ORDER BY nc.created_at ASC
        """, (note_id,)).fetchall()


# ── 群组 ──────────────────────────────────────────────────────────────────────

def create_group(name: str, course_key: str) -> int:
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO groups (name, course_key) VALUES (?,?)",
            (name, course_key),
        )
        row = conn.execute("SELECT id FROM groups WHERE course_key=?", (course_key,)).fetchone()
        return row["id"]


def get_group_by_course_key(course_key: str) -> sqlite3.Row | None:
    with _conn() as conn:
        return conn.execute("SELECT * FROM groups WHERE course_key=?", (course_key,)).fetchone()


def add_group_member(group_id: int, user_id: int) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO group_members (group_id, user_id) VALUES (?,?)",
            (group_id, user_id),
        )


def get_user_groups_with_unread(user_id: int) -> list:
    with _conn() as conn:
        return conn.execute("""
            SELECT g.id, g.name, g.course_key,
                   (SELECT COUNT(*) FROM group_messages gm
                    WHERE gm.group_id = g.id
                      AND gm.created_at > COALESCE(gme.last_read_at, '1970-01-01')
                      AND gm.sender_id != ?) as unread,
                   (SELECT gm2.content FROM group_messages gm2
                    WHERE gm2.group_id = g.id
                    ORDER BY gm2.created_at DESC LIMIT 1) as last_content,
                   (SELECT gm3.created_at FROM group_messages gm3
                    WHERE gm3.group_id = g.id
                    ORDER BY gm3.created_at DESC LIMIT 1) as last_at
            FROM groups g
            JOIN group_members gme ON gme.group_id = g.id AND gme.user_id = ?
            ORDER BY (last_at IS NULL), last_at DESC
        """, (user_id, user_id)).fetchall()


def send_group_message(group_id: int, sender_id: int, content: str) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO group_messages (group_id, sender_id, content) VALUES (?,?,?)",
            (group_id, sender_id, content),
        )
        return cur.lastrowid


def get_group_messages(group_id: int, date: str | None = None) -> list:
    with _conn() as conn:
        if date:
            return conn.execute("""
                SELECT gm.id, gm.group_id, gm.sender_id, gm.content, gm.created_at,
                       u.username as sender_username, u.nickname as sender_nickname,
                       u.role as sender_role, u.avatar as sender_avatar
                FROM group_messages gm
                JOIN users u ON u.id = gm.sender_id
                WHERE gm.group_id = ? AND date(gm.created_at) = ?
                ORDER BY gm.created_at ASC
            """, (group_id, date)).fetchall()
        return conn.execute("""
            SELECT gm.id, gm.group_id, gm.sender_id, gm.content, gm.created_at,
                   u.username as sender_username, u.nickname as sender_nickname,
                   u.role as sender_role, u.avatar as sender_avatar
            FROM group_messages gm
            JOIN users u ON u.id = gm.sender_id
            WHERE gm.group_id = ?
            ORDER BY gm.created_at ASC
        """, (group_id,)).fetchall()


def mark_group_read(group_id: int, user_id: int) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE group_members SET last_read_at=datetime('now','localtime') WHERE group_id=? AND user_id=?",
            (group_id, user_id),
        )


def get_group_unread_total(user_id: int) -> int:
    with _conn() as conn:
        row = conn.execute("""
            SELECT COALESCE(SUM(
                (SELECT COUNT(*) FROM group_messages gm
                 WHERE gm.group_id = gme.group_id
                   AND gm.created_at > COALESCE(gme.last_read_at, '1970-01-01')
                   AND gm.sender_id != ?)
            ), 0) as total
            FROM group_members gme WHERE gme.user_id = ?
        """, (user_id, user_id)).fetchone()
        return row["total"] if row else 0


def get_group_members(group_id: int) -> list:
    with _conn() as conn:
        return conn.execute("""
            SELECT u.id, u.username, u.nickname, u.avatar, u.role, gm.joined_at
            FROM group_members gm
            JOIN users u ON u.id = gm.user_id
            WHERE gm.group_id = ?
            ORDER BY u.role DESC, gm.joined_at ASC
        """, (group_id,)).fetchall()


def pin_group_message(group_id: int, message_id: int, user_id: int) -> None:
    with _conn() as conn:
        count = conn.execute("SELECT COUNT(*) as c FROM group_pins WHERE group_id=?", (group_id,)).fetchone()["c"]
        if count >= 2:
            oldest = conn.execute("SELECT id FROM group_pins WHERE group_id=? ORDER BY pinned_at ASC LIMIT 1", (group_id,)).fetchone()
            if oldest:
                conn.execute("DELETE FROM group_pins WHERE id=?", (oldest["id"],))
        conn.execute("INSERT OR IGNORE INTO group_pins (group_id, message_id, pinned_by) VALUES (?,?,?)", (group_id, message_id, user_id))


def unpin_group_message(group_id: int, message_id: int) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM group_pins WHERE group_id=? AND message_id=?", (group_id, message_id))


def get_group_pins(group_id: int) -> list:
    with _conn() as conn:
        return conn.execute("""
            SELECT gp.id, gp.group_id, gp.message_id, gp.pinned_by, gp.pinned_at,
                   gm.content, gm.created_at as msg_at,
                   u.username as pinner_name, u.nickname as pinner_nickname
            FROM group_pins gp
            JOIN group_messages gm ON gm.id = gp.message_id
            JOIN users u ON u.id = gp.pinned_by
            WHERE gp.group_id = ?
            ORDER BY gp.pinned_at ASC
        """, (group_id,)).fetchall()


def get_group_dates(group_id: int) -> list:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT date(created_at) as d FROM group_messages WHERE group_id=? ORDER BY d ASC",
            (group_id,),
        ).fetchall()
        return [r["d"] for r in rows]


# ── 私聊置顶 ──────────────────────────────────────────────────────────────────

def set_private_pin(user_id: int, other_id: int, message_id: int) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO conversation_pins (user_id, other_id, message_id) VALUES (?,?,?)",
            (user_id, other_id, message_id),
        )


def get_private_pin(user_id: int, other_id: int) -> sqlite3.Row | None:
    with _conn() as conn:
        return conn.execute("""
            SELECT cp.message_id, cp.pinned_at, m.content, m.created_at as msg_at, m.sender_id
            FROM conversation_pins cp
            JOIN messages m ON m.id = cp.message_id
            WHERE cp.user_id = ? AND cp.other_id = ?
        """, (user_id, other_id)).fetchone()


def delete_private_pin(user_id: int, other_id: int) -> None:
    with _conn() as conn:
        conn.execute(
            "DELETE FROM conversation_pins WHERE user_id=? AND other_id=?",
            (user_id, other_id),
        )


# ── 用户公开资料 ──────────────────────────────────────────────────────────────

def get_user_public_profile(user_id: int) -> sqlite3.Row | None:
    with _conn() as conn:
        return conn.execute(
            "SELECT id, username, nickname, role, gender, phone, avatar FROM users WHERE id=?",
            (user_id,),
        ).fetchone()


# ── 私聊历史（按日期） ────────────────────────────────────────────────────────

def get_conversation_dates(user_id: int, other_id: int) -> list:
    with _conn() as conn:
        rows = conn.execute("""
            SELECT DISTINCT date(created_at) as d FROM messages
            WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
            ORDER BY d ASC
        """, (user_id, other_id, other_id, user_id)).fetchall()
        return [r["d"] for r in rows]


def get_conversation_messages_by_date(user_id: int, other_id: int, date: str) -> list:
    with _conn() as conn:
        return conn.execute("""
            SELECT m.id, m.sender_id, m.receiver_id, m.content, m.is_read, m.created_at,
                   s.username as sender_name, s.nickname as sender_nickname,
                   s.avatar as sender_avatar, s.role as sender_role
            FROM messages m
            JOIN users s ON s.id = m.sender_id
            WHERE ((m.sender_id=? AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=?))
              AND date(m.created_at) = ?
            ORDER BY m.created_at ASC
        """, (user_id, other_id, other_id, user_id, date)).fetchall()


# ── 个人日程 ──────────────────────────────────────────────────────────────────

def get_user_schedules(user_id: int, year: int, month: int) -> list:
    prefix = f"{year}-{month:02d}"
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM schedules WHERE user_id=? AND date LIKE ? ORDER BY date ASC",
            (user_id, f"{prefix}%"),
        ).fetchall()


def create_schedule(user_id: int, date: str, title: str, content: str) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO schedules (user_id, date, title, content) VALUES (?,?,?,?)",
            (user_id, date, title, content),
        )
        return cur.lastrowid


def update_schedule(schedule_id: int, user_id: int, title: str, content: str) -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE schedules SET title=?, content=? WHERE id=? AND user_id=?",
            (title, content, schedule_id, user_id),
        )
        return cur.rowcount > 0


def delete_schedule(schedule_id: int, user_id: int) -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "DELETE FROM schedules WHERE id=? AND user_id=?",
            (schedule_id, user_id),
        )
        return cur.rowcount > 0


# ── 公开日程 ──────────────────────────────────────────────────────────────────

def create_public_schedule(teacher_id: int, course_key: str, date: str, title: str, content: str) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO public_schedules (teacher_id, course_key, date, title, content) VALUES (?,?,?,?,?)",
            (teacher_id, course_key, date, title, content),
        )
        schedule_id = cur.lastrowid
        students = conn.execute(
            "SELECT student_id FROM course_members WHERE course_key=?", (course_key,)
        ).fetchall()
        for s in students:
            conn.execute(
                "INSERT OR IGNORE INTO schedule_notifications (user_id, schedule_id, type) VALUES (?,?,?)",
                (s["student_id"], schedule_id, "new"),
            )
        return schedule_id


def cancel_public_schedule(schedule_id: int, teacher_id: int) -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE public_schedules SET cancelled=1, cancelled_at=datetime('now','localtime') "
            "WHERE id=? AND teacher_id=? AND cancelled=0",
            (schedule_id, teacher_id),
        )
        if cur.rowcount == 0:
            return False
        row = conn.execute("SELECT course_key FROM public_schedules WHERE id=?", (schedule_id,)).fetchone()
        if row:
            students = conn.execute(
                "SELECT student_id FROM course_members WHERE course_key=?", (row["course_key"],)
            ).fetchall()
            for s in students:
                conn.execute(
                    "INSERT OR IGNORE INTO schedule_notifications (user_id, schedule_id, type) VALUES (?,?,?)",
                    (s["student_id"], schedule_id, "cancel"),
                )
        return True


def get_public_schedules_for_user(user_id: int, year: int, month: int) -> list:
    """返回该用户可见的所有公开日程（学生：已选课程；教师：自己发布的）。
    含 is_read、teacher_name、course_name 字段，按日期升序排列。"""
    prefix = f"{year}-{month:02d}"
    with _conn() as conn:
        role_row = conn.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
        if not role_row:
            return []
        if role_row["role"] == "student":
            return conn.execute("""
                SELECT ps.*, u.username as teacher_username, u.nickname as teacher_nickname,
                       c.name as course_name,
                       (SELECT COUNT(*) FROM public_schedule_reads psr
                        WHERE psr.schedule_id = ps.id AND psr.user_id = ?) as is_read
                FROM public_schedules ps
                JOIN users u ON u.id = ps.teacher_id
                JOIN courses c ON c.course_key = ps.course_key
                WHERE ps.course_key IN (SELECT course_key FROM course_members WHERE student_id=?)
                  AND ps.date LIKE ?
                ORDER BY ps.date ASC
            """, (user_id, user_id, f"{prefix}%")).fetchall()
        else:
            return conn.execute("""
                SELECT ps.*, u.username as teacher_username, u.nickname as teacher_nickname,
                       c.name as course_name, 1 as is_read
                FROM public_schedules ps
                JOIN users u ON u.id = ps.teacher_id
                JOIN courses c ON c.course_key = ps.course_key
                WHERE ps.teacher_id = ? AND ps.date LIKE ?
                ORDER BY ps.date ASC
            """, (user_id, f"{prefix}%")).fetchall()


def mark_public_schedule_read(user_id: int, schedule_id: int) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO public_schedule_reads (user_id, schedule_id) VALUES (?,?)",
            (user_id, schedule_id),
        )


def get_calendar_dots(user_id: int, year: int, month: int) -> dict:
    """返回 {date_str: {blue_count, red_count, unread}} 字典，仅含有日程的日期。"""
    prefix = f"{year}-{month:02d}"
    result: dict = {}
    with _conn() as conn:
        personal = conn.execute(
            "SELECT date, COUNT(*) as cnt FROM schedules WHERE user_id=? AND date LIKE ? GROUP BY date",
            (user_id, f"{prefix}%"),
        ).fetchall()
        for r in personal:
            result.setdefault(r["date"], {"blue_count": 0, "red_count": 0, "unread": False})
            result[r["date"]]["blue_count"] = r["cnt"]

        role_row = conn.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
        if not role_row:
            return result

        if role_row["role"] == "student":
            public = conn.execute("""
                SELECT ps.date,
                       COUNT(*) as cnt,
                       SUM(CASE WHEN psr.schedule_id IS NULL THEN 1 ELSE 0 END) as unread_cnt
                FROM public_schedules ps
                LEFT JOIN public_schedule_reads psr
                       ON psr.schedule_id = ps.id AND psr.user_id = ?
                WHERE ps.course_key IN (SELECT course_key FROM course_members WHERE student_id=?)
                  AND ps.date LIKE ? AND ps.cancelled = 0
                GROUP BY ps.date
            """, (user_id, user_id, f"{prefix}%")).fetchall()
        else:
            public = conn.execute(
                "SELECT date, COUNT(*) as cnt, 0 as unread_cnt FROM public_schedules WHERE teacher_id=? AND date LIKE ? AND cancelled=0 GROUP BY date",
                (user_id, f"{prefix}%"),
            ).fetchall()

        for r in public:
            d = r["date"]
            result.setdefault(d, {"blue_count": 0, "red_count": 0, "unread": False})
            result[d]["red_count"] = r["cnt"]
            if r["unread_cnt"] > 0:
                result[d]["unread"] = True

    return result


# ── 日程通知 ──────────────────────────────────────────────────────────────────

def get_unshown_notifications(user_id: int) -> list:
    with _conn() as conn:
        return conn.execute("""
            SELECT sn.id, sn.type, sn.created_at,
                   ps.date, ps.title, ps.course_key,
                   u.username as teacher_username, u.nickname as teacher_nickname,
                   c.name as course_name
            FROM schedule_notifications sn
            JOIN public_schedules ps ON ps.id = sn.schedule_id
            JOIN users u ON u.id = ps.teacher_id
            JOIN courses c ON c.course_key = ps.course_key
            WHERE sn.user_id = ? AND sn.shown = 0
            ORDER BY sn.created_at ASC
        """, (user_id,)).fetchall()


def mark_notification_shown(notification_id: int, user_id: int) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE schedule_notifications SET shown=1 WHERE id=? AND user_id=?",
            (notification_id, user_id),
        )
