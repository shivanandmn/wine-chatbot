import json
import logging
from enum import Enum
from functools import lru_cache
from typing import Annotated, Any, Self

from pydantic import BaseModel, Field, HttpUrl, model_validator
from slugify import slugify

from memory_agent.constants import (
    acidity_adj,
    alcohol_adj,
    body_adj,
    intensity_adj,
    sweetness_adj,
    tannin_adj,
)
from memory_agent.settings import get_settings
from memory_agent.constants import AROMAS_IMAGE_ROOT

logger = logging.getLogger(__name__)
s = get_settings()


class TasteProfileName(str, Enum):
    acidity = "acidity"
    intensity = "intensity"
    sweetness = "sweetness"
    tannin = "tannin"
    body = "body"
    alcohol = "alcohol"


class TasteProfile(BaseModel):
    name: TasteProfileName
    step: Annotated[float, Field(ge=0, le=5)] | None = None
    value: Any = None

    text: str

    @classmethod
    def parse(cls, values):
        if "text" not in values:
            values["text"] = get_adj_text_for_taste_profile(values["name"], values["value"])

            if values["name"] == TasteProfileName.alcohol and isinstance(values["value"], str):
                values["step"] = ["VL", "L", "M", "MH", "H", "VH"].index(values["value"].upper())
                values["value"] = {
                    "VL": "Very Low",
                    "L": "Low",
                    "M": "Medium",
                    "MH": "Medium High",
                    "H": "High",
                    "VH": "Very High",
                }.get(values["value"], "")

            if "step" not in values:
                values["step"] = values.get("value", 0)

        return cls(**values)


class TasteFlavor(BaseModel):
    group: str | None = None
    sub_groups: list[str]

    @classmethod
    def parse(cls, flavor: str):
        return cls(
            sub_groups=[flavor],
            group=get_group_from_sub_groups(flavor),
        )


class Aroma(BaseModel):
    slug: str = Field(default=..., description="Lowercase with hyphens")
    display_name: str = Field(default=..., description="initial caps with spaces")
    image_url: HttpUrl

    @classmethod
    def from_name(cls, name: str) -> Self:
        """Input `Aroma` name, lowercase with spaces"""
        slug = slugify(name)
        # TODO: a few aromas share the same image data and we may not benefit from caching with this implementation
        return cls(slug=slugify(name), display_name=name.title(), image_url=f"{AROMAS_IMAGE_ROOT}/{slug}.webp")  # type: ignore


class Taste(BaseModel):
    profiles: list[TasteProfile] = Field(default_factory=list)
    flavors: list[TasteFlavor] = Field(
        default_factory=list,
        description='backward compatibility for "vinovoss.com", deprecated',
        deprecated=True,
    )
    aromas: list[str] = Field(default_factory=list, deprecated=True, description="Flat list of aroma names")
    aromas_structured: list[Aroma] | None = Field(
        default=None, description="Source of truth for `Aroma` display, with image URL included"
    )

    @model_validator(mode="after")
    def populate_aromas_structured(self) -> Self:
        # Relies on `aromas` being populated from DB, so will need updating if we remove that field
        if len(self.aromas) > 0:
            self.aromas_structured = [Aroma.from_name(item) for item in self.aromas]
        return self

    @classmethod
    def parse(cls, values):
        profiles = [TasteProfile.parse(dict(name=key, value=values.get(key, 0))) for key in TasteProfileName]

        aromas = values.get("flavors") or values.get("aromas") or []
        flavors = [TasteFlavor.parse(flavor) for flavor in aromas] if aromas else []
        merged_flavors = []
        for flavor in flavors:
            for f in merged_flavors:
                if f.group == flavor.group:
                    f.sub_groups.extend(flavor.sub_groups)
                    break
            else:
                merged_flavors.append(flavor)

        return cls(profiles=profiles, flavors=merged_flavors, aromas=aromas)


@lru_cache
def get_flavor_group_mapping() -> dict[str, str]:
    file = s.weight_dir / "flavor_group_mapping.json"
    with open(file, encoding="utf8") as f:
        return json.load(f)


def get_group_from_sub_groups(sub_group: str) -> str:
    if group := get_flavor_group_mapping().get(sub_group):
        return group

    logger.warning(f"⚠ Invalid sub group {sub_group}")
    return ""


def get_adj_text_for_taste_profile(profile_name: TasteProfileName, value: float) -> str:
    if not value:
        return f"No {profile_name.value.title()}"

    if profile_name == TasteProfileName.alcohol:
        for adj, adj_value in alcohol_adj:
            if adj_value == value:
                return adj
    else:
        if profile_name == TasteProfileName.sweetness:
            adj_list = sweetness_adj
        elif profile_name == TasteProfileName.intensity:
            adj_list = intensity_adj
        elif profile_name == TasteProfileName.body:
            adj_list = body_adj
        elif profile_name == TasteProfileName.acidity:
            adj_list = acidity_adj
        elif profile_name == TasteProfileName.tannin:
            adj_list = tannin_adj
        else:
            raise ValueError(f"Invalid profile name {profile_name}")

        for adj, adj_value in adj_list:
            if value < adj_value:
                return adj
        return adj_list[-1][0]

    raise ValueError(f"Invalid value {value} for profile {profile_name}")


class TasteProfileOut(BaseModel):
    name: TasteProfileName
    value: Annotated[float, Field(ge=0, le=5)] | None = None
    text: str


class TasteFlavorOut(BaseModel):
    group: str
    sub_groups: list[str]


class TasteOut(BaseModel):
    profiles: list[TasteProfileOut] = Field(default_factory=list)
    flavors: list[TasteFlavorOut] = Field(default_factory=list)
