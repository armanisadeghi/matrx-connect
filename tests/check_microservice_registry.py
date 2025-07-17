import asyncio, dotenv
dotenv.load_dotenv()

from matrx_connect.microservices import MicroserviceFactory
from matrx_utils import vcprint

async def main():
    client = await MicroserviceFactory.create_or_get_client_from_url(name="matrx-scraper", url="http://localhost:8001")
    response = await client.api_call_default("mic_check", {"mic_check_message": "matrx-connect says hi."})
    vcprint(response,color="gold")

if __name__ == '__main__':
    asyncio.run(main())
