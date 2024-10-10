from parsers.rinex_parser import RinexParser
from fastapi import UploadFile, HTTPException
from typing import Optional

from config import logger

class ParserManager:
    def __init__(self):
        logger.debug("Initializing ParserManager")
        self.parser: Optional[RinexParser] = None

    async def set_parser(self, rinex_file: UploadFile):
        logger.info(f"Setting parser for file: {rinex_file.filename}")
        try:
            self.parser = await RinexParser.create(rinex_file)
            logger.debug(f"Parser successfully created for file: {rinex_file.filename}")
        except Exception as e:
            logger.error(f"Error while creating parser for file {rinex_file.filename}: {e}")
            raise HTTPException(status_code=500, detail="Error initializing parser")

    def get_parser(self) -> RinexParser:
        if self.parser is None:
            logger.warning("Attempted to access parser before initialization")
            raise HTTPException(status_code=400, detail="Parser not initialized")
        return self.parser

async def get_parser_manager() -> ParserManager:
    return parser_manager

parser_manager = ParserManager()
