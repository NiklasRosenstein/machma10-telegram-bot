
from pathlib import Path

import toml
from databind.core import datamodel, field
from databind.json import from_json


@datamodel(strict=True)
class Config:
  api_token: str = field(altname='api-token')
  database_url: str = field(altname='database-url')

  @classmethod
  def load(self, file: Path) -> 'Config':
    raw = toml.load(file)
    return from_json(Config, raw)
