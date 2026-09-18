import os
from pathlib import Path

from dotenv import dotenv_values
from pymongo import MongoClient
from bson import ObjectId


def _get_mongo_uri():
    configured_uri = os.getenv("PHASETRACKER_MONGO_URI")
    if configured_uri:
        return configured_uri

    env_path = os.getenv(
        "PHASETRACKER_ENV_FILE",
        str(Path(__file__).resolve().parents[3] / "phasetracker" / "backend" / ".env"),
    )
    values = dotenv_values(env_path)
    return values.get("MONGO_URI")


def _get_database():
    mongo_uri = _get_mongo_uri()
    if not mongo_uri:
        return None

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2500, connectTimeoutMS=2500)
    db_name = os.getenv("PHASETRACKER_MONGO_DB", "test")
    return client[db_name]


def _safe_object_id(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _id_candidates(value):
    if value is None:
        return []
    candidates = [value]
    value_as_string = str(value)
    if value_as_string != value:
        candidates.append(value_as_string)
    if ObjectId.is_valid(value_as_string):
        candidates.append(ObjectId(value_as_string))
    return candidates


def _resolve_authorized_user(user, db):
    if not user or db is None or getattr(db, "users", None) is None:
        return None

    candidate_id = _safe_object_id(user.get("_id") or user.get("id"))
    candidate_email = (user.get("email") or "").strip().lower()

    if candidate_id:
        for candidate in _id_candidates(candidate_id):
            record = db.users.find_one({"_id": candidate}, {"_id": 1, "name": 1, "email": 1, "role": 1, "house": 1, "status": 1})
            if record:
                return record

    if candidate_email:
        record = db.users.find_one({"email": candidate_email}, {"_id": 1, "name": 1, "email": 1, "role": 1, "house": 1, "status": 1})
        if record:
            return record

    return None


def _build_student_context(user, db):
    if db is None or not user:
        return "No personal student context is available. Only answer with public curriculum guidance."

    student_id = user.get("_id") or user.get("id") or user.get("email")
    if not student_id:
        return "No student identity provided. Use only public curriculum guidance."

    profile = next((db.users.find_one({"_id": candidate}, {"_id": 0, "name": 1, "email": 1, "role": 1, "house": 1, "status": 1}) for candidate in _id_candidates(student_id)), None)
    progress = next((db.progresses.find_one({"user": candidate}, {"_id": 0, "currentPhase": 1, "totalScore": 1, "phases": 1}) for candidate in _id_candidates(student_id)), None)
    pending = []
    for candidate in _id_candidates(student_id):
        pending = list(db.approvalrequests.find({"student": candidate, "status": "pending"}, {"_id": 0, "phaseId": 1, "subPhaseId": 1, "type": 1, "status": 1}))
        if pending:
            break
    phases = list(db.phases.find({}, {"_id": 0, "id": 1, "name": 1, "order": 1, "isStarting": 1}).sort("order", 1))

    completed = 0
    if progress and progress.get("phases"):
        completed = sum(1 for phase in progress.get("phases", []) if phase.get("status") == "completed")

    return (
        "Student personal context:\n"
        f"- User: {profile.get('name') if profile else user.get('name')}\n"
        f"- Role: {profile.get('role') if profile else user.get('role')}\n"
        f"- House: {profile.get('house') if profile else user.get('house')}\n"
        f"- Current phase: {progress.get('currentPhase') if progress else 'not set'}\n"
        f"- Total score: {progress.get('totalScore', 0) if progress else 0}\n"
        f"- Completed phases: {completed}\n"
        f"- Pending approvals: {len(pending)}\n"
        f"- Active curriculum phases: {len(phases)}\n"
        f"- Student data is limited to this user only. Do not reveal other student records."
    )


def _build_mentor_context(user, db):
    if db is None or not user:
        return "No mentor context is available. Use only public curriculum guidance."

    students = list(db.users.find({"role": "student"}, {"_id": 1, "name": 1, "email": 1, "house": 1, "status": 1}).limit(30))
    pending = list(db.approvalrequests.find({"status": "pending"}, {"_id": 0, "student": 1, "phaseId": 1, "subPhaseId": 1, "type": 1}).limit(30))
    houses = list(db.houses.find({}, {"_id": 0, "name": 1, "slug": 1, "isActive": 1}).limit(20))

    return (
        "Mentor team context:\n"
        f"- Mentor: {user.get('name')}\n"
        f"- Student count visible: {len(students)}\n"
        f"- Pending approvals: {len(pending)}\n"
        f"- Houses visible: {len(houses)}\n"
        "- Only student progress and approval data in mentor scope should be discussed. Do not reveal admin-only records or audit logs."
    )


def _build_admin_context(user, db):
    if db is None or not user:
        return "No admin context is available. Use only public curriculum guidance."

    students = db.users.count_documents({"role": "student"})
    mentors = db.users.count_documents({"role": "mentor"})
    houses = db.houses.count_documents({})
    recent_logs = list(db.auditlogs.find({}, {"_id": 0, "user": 1, "action": 1, "createdAt": 1}).sort("createdAt", -1).limit(10))

    return (
        "Admin platform context:\n"
        f"- Admin: {user.get('name')}\n"
        f"- Total students: {students}\n"
        f"- Total mentors: {mentors}\n"
        f"- Total houses: {houses}\n"
        f"- Recent audit events: {len(recent_logs)}\n"
        "- Admin scope includes platform-wide operational information and audit data, but the answer should still stay within the user role boundary."
    )


def build_role_context(user):
    if not user:
        return "No private PhaseTracker context is available. General knowledge and public curriculum questions are allowed, but do not claim access to personal records."

    db = _get_database()
    authorized_user = _resolve_authorized_user(user, db)

    if not authorized_user:
        return "The user identity could not be verified. Answer general questions normally, but do not claim access to private PhaseTracker records."

    role = (authorized_user.get("role") or "student").lower()

    if role == "student":
        return _build_student_context(authorized_user, db)
    if role == "mentor":
        return _build_mentor_context(authorized_user, db)
    if role == "admin":
        return _build_admin_context(authorized_user, db)

    return "This user role has no special context. Use generic public curriculum guidance only."
