class DomainException(Exception):
    """Base domain exception for Sortling."""
    pass

class UniversityNotFoundException(DomainException):
    def __init__(self, university_id: int):
        super().__init__(f"University with ID {university_id} not found.")

class SessionNotFoundException(DomainException):
    def __init__(self, session_id: str):
        super().__init__(f"Recommendation session {session_id} not found.")

class QuestionNotFoundException(DomainException):
    def __init__(self, question_id: int):
        super().__init__(f"Question with ID {question_id} not found.")

class ClubNotFoundException(DomainException):
    def __init__(self, club_id: int):
        super().__init__(f"Club with ID {club_id} not found.")

class ImportFailedException(DomainException):
    def __init__(self, reason: str):
        super().__init__(f"Import job failed: {reason}")
