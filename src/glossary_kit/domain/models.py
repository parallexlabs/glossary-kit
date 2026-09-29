from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from glossary_kit.domain.urls import is_safe_http_url


class TermStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    DEPRECATED = "deprecated"


class ReuseStatus(StrEnum):
    VERIFIED_OPEN = "verified_open"
    LICENCE_NOT_VERIFIED = "licence_not_verified"
    EXCLUDED = "excluded"


class PublicationVisibility(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"


class Publication(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visibility: PublicationVisibility = PublicationVisibility.PUBLIC


def _validate_optional_url(value: str | None) -> str | None:
    if value is None:
        return None
    if not is_safe_http_url(value):
        msg = (
            "URL must be an absolute http or https URL "
            "(javascript:, data:, protocol-relative and malformed URLs are rejected)"
        )
        raise ValueError(msg)
    return value


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str | None = None
    citation: str | None = None

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str | None) -> str | None:
        return _validate_optional_url(v)


class DictionaryBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    header: str
    term_id: str


class Term(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    preferred_label: str
    definition: str
    status: TermStatus
    language: str = "en"
    abbreviation: str | None = None
    synonyms: list[str] = Field(default_factory=list)
    domain: str | None = None
    steward: str | None = None
    version: str | None = None
    sources: list[Source] = Field(default_factory=list)
    source_url: str | None = None
    licence: str | None = None
    licence_url: str | None = None
    definition_method: str | None = None
    reuse_status: ReuseStatus | None = None
    attribution: str | None = None
    demo: bool = False
    related_terms: list[str] = Field(default_factory=list)
    classification: str | None = None
    dictionary_bindings: list[DictionaryBinding] = Field(default_factory=list)
    publication: Publication | None = None
    replaces: str | None = None
    replaced_by: str | None = None

    @field_validator("synonyms", mode="before")
    @classmethod
    def _coerce_synonyms(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [s.strip() for s in v.split("|") if s.strip()]
        return list(v)

    @field_validator("source_url", "licence_url")
    @classmethod
    def _validate_urls(cls, v: str | None) -> str | None:
        return _validate_optional_url(v)


class GlossaryMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str | None = None
    schema_version: str = "1.0.0"
    language: str = "en"
    attribution: str | None = None
    publisher: str | None = None


class Glossary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metadata: GlossaryMetadata
    terms: list[Term]

    @model_validator(mode="after")
    def _non_empty_terms(self) -> Glossary:
        if not self.terms:
            msg = "Glossary must contain at least one term"
            raise ValueError(msg)
        return self

    def term_ids(self) -> set[str]:
        return {t.id for t in self.terms}

    def term_by_id(self, term_id: str) -> Term | None:
        for t in self.terms:
            if t.id == term_id:
                return t
        return None

    def public_terms(self) -> list[Term]:
        result: list[Term] = []
        for t in self.terms:
            vis = t.publication.visibility if t.publication else PublicationVisibility.PUBLIC
            if vis == PublicationVisibility.PUBLIC:
                result.append(t)
        return result
