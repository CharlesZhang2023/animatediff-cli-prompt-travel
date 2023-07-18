import json
import logging
from functools import lru_cache
from os import PathLike
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseConfig, BaseSettings, Field, validator
from pydantic.env_settings import (
    EnvSettingsSource,
    InitSettingsSource,
    SecretsSettingsSource,
    SettingsSourceCallable,
)

from animatediff import get_dir

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JsonSettingsSource:
    __slots__ = ["json_config_path"]

    def __init__(
        self,
        json_config_path: Optional[Union[PathLike, list[PathLike]]] = list(),
    ) -> None:
        if isinstance(json_config_path, list):
            self.json_config_path = [Path(path) for path in json_config_path]
        else:
            self.json_config_path = [Path(json_config_path)] if json_config_path is not None else []

    def __call__(self, settings: BaseSettings) -> Dict[str, Any]:  # noqa C901
        classname = settings.__class__.__name__
        encoding = settings.__config__.env_file_encoding
        if len(self.json_config_path) == 0:
            pass  # no json config provided

        merged_config = dict()  # create an empty dict to merge configs into
        for idx, path in enumerate(self.json_config_path):
            if path.exists() and path.is_file():  # check if the path exists and is a file
                logger.debug(f"{classname}: loading config #{idx+1} from {path}")
                merged_config.update(json.loads(path.read_text(encoding=encoding)))
                logger.debug(f"{classname}: config state #{idx+1}: {merged_config}")
            else:
                raise FileNotFoundError(f"{classname}: config #{idx+1} at {path} not found or not a file")

        logger.debug(f"{classname}: loaded config: {merged_config}")
        return merged_config  # return the merged config

    def __repr__(self) -> str:
        return f"JsonSettingsSource(json_config_path={repr(self.json_config_path)})"


class JsonConfig(BaseConfig):
    json_config_path: Optional[Union[Path, list[Path]]] = None
    env_file_encoding: str = "utf-8"

    @classmethod
    def customise_sources(
        cls,
        init_settings: InitSettingsSource,
        env_settings: EnvSettingsSource,
        file_secret_settings: SecretsSettingsSource,
    ) -> Tuple[SettingsSourceCallable, ...]:
        # pull json_config_path from init_settings if passed, otherwise use the class var
        json_config_path = init_settings.init_kwargs.pop("json_config_path", cls.json_config_path)

        logger.debug(f"Using JsonSettingsSource for {cls.__name__}")
        json_settings = JsonSettingsSource(json_config_path=json_config_path)

        # return the new settings sources
        return (
            init_settings,
            json_settings,
        )


class InferenceConfig(BaseSettings):
    unet_additional_kwargs: dict[str, Any]
    noise_scheduler_kwargs: dict[str, Any]

    class Config(JsonConfig):
        json_config_path: Path


@lru_cache(maxsize=2)
def get_infer_config(
    config_path: Path = get_dir("config").joinpath("inference/default.json"),
) -> InferenceConfig:
    settings = InferenceConfig(json_config_path=config_path)
    return settings


class ModelConfig(BaseSettings):
    name: str = Field(...)  # Config name, not actually used for much of anything
    base: str = Field(...)
    path: Path = Field(...)  # Path to the model checkpoint, relative to cwd()
    motion_module: Path = Field(...)  # Paths to the motion modules, relative to cwd()
    seed: list[int] = Field([])  # Seeds for the random number generators
    steps: int = 25  # Number of inference steps to run
    guidance_scale: float = 7.5  # CFG scale to use
    prompt: list[str] = Field([])  # Prompts to use
    n_prompt: list[str] = Field([])  # Anti-prompts to use

    class Config(JsonConfig):
        json_config_path: Path


@lru_cache(maxsize=2)
def get_model_config(config_path: Path) -> ModelConfig:
    settings = ModelConfig(json_config_path=config_path)
    return settings
