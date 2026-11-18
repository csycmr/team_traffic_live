"""API 응답 형태. 화면 JavaScript가 읽는 필드 이름을 여기서 고정한다."""

from pydantic import BaseModel, Field


class OecdCountry(BaseModel):
    country: str
    iso3: str
    rate: float = Field(ge=0)
    rank: int = Field(ge=1)


class OecdYear(BaseModel):
    year: int
    country_count: int = Field(ge=0)
    countries: list[OecdCountry]


class OecdRankings(BaseModel):
    years: list[OecdYear]


class AccidentTrendYear(BaseModel):
    year: int
    nationwide_accidents: int = Field(ge=0)
    seoul_accidents: int = Field(ge=0)
    seoul_injuries: int = Field(ge=0)
    seoul_deaths: int = Field(ge=0)


class AccidentTrend(BaseModel):
    years: list[AccidentTrendYear]


class ChildPedestrian(BaseModel):
    """서울 어린이(12세 이하) 보행자 교통사고."""

    year: int
    accidents: int = Field(ge=0)
    deaths: int = Field(ge=0)


class ElderlyPedestrian(BaseModel):
    """서울 고령(65세 이상) 보행자 교통사고 자치구 합계."""

    year: int
    region: str
    districts: int
    accidents: int = Field(ge=0)
    deaths: int = Field(ge=0)
    injuries: int = Field(ge=0)
