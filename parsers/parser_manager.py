from parsers.rinex_parser import RinexParser
from fastapi import UploadFile, HTTPException
from typing import Optional

class ParserManager:
    def __init__(self):
        self.parser: Optional[RinexParser] = None

    async def set_parser(self, rinex_file: UploadFile):
        self.parser = await RinexParser.create(rinex_file)

    def get_parser(self) -> RinexParser:
        if self.parser is None:
            raise HTTPException(status_code=400, detail="Parser not initialized")
        return self.parser

async def get_parser_manager() -> ParserManager:
    return parser_manager

parser_manager = ParserManager()
