import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARN)

def get_character_corp(self, character_id: int) -> int:
  """
  Get the corporation id of a character.

  :param character_id: The ID of the character to get the corporation for.
  :return: The corporation ID of the character.
  """

  response = self._post('characters/affiliation', json=[str(character_id)])
  return response[0]['corporation_id']


def get_character_alliance(self, character_id: int) -> int | None:
  response = self._get(f'characters/{character_id}/')
  return response.get('alliance_id', None)


def get_alliances_for_characters(self, ids: list[int]) -> dict[int, int | None]:
  CHUNK_SIZE = 1000
  character_lists = [ids[i : i + CHUNK_SIZE] for i in range(0, len(ids), CHUNK_SIZE)]
  output = {}

  for chunk in character_lists:
    response = self._post('characters/affiliation', json=chunk)

    for item in response:
      if 'character_id' in item:
        output[item['character_id']] = (
          int(item['alliance_id']) if 'alliance_id' in item else None
        )

  return output
