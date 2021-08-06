from sqlalchemy import Column, Integer, String, Text

from models.models import Base, auto_str

__all__ = ["FilamentType"]


@auto_str
class FilamentType(Base):
    FILLAMENTUM = "fillamentum"
    PRUSAMENT = "prusament"

    __tablename__ = "filament_types"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(Text, nullable=False, unique=True)
    profile = Column(String, default=FILLAMENTUM)
    image_path = Column(String, nullable=False, unique=True)

    @staticmethod
    def verify_type(type_str: str) -> bool:
        return {FilamentType.FILLAMENTUM: True, FilamentType.PRUSAMENT: True}.get(
            type_str.casefold(), False
        )
