import json
from pathlib import Path
import shutil
from urllib.request import Request, urlopen


STATES = [
    "AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL",
    "GA", "HI", "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA",
    "MD", "ME", "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE",
    "NH", "NJ", "NM", "NV", "NY", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV",
    "WY",
]


def download(year: int) -> None:
    directory = Path(f"data/nibrs/{year}")
    directory.mkdir(exist_ok=True)

    for state in STATES:
        file = f"{state}-{year}.zip"
        key = f"nibrs/incident/{year}/{file}"
        url = f"https://cde.ucr.cjis.gov/LATEST/s3/signedurl?key={key}"

        with urlopen(Request(url, None, {})) as response:
            if response.status != 200:
                raise ValueError(f"received {response.status} when accessing {url}")
            body = response.read()

        mapping = json.loads(body)
        if len(mapping) == 0:
            print(f"skipping {file} due to empty signedurl response")
            continue

        if key not in mapping:
            raise ValueError(f'key "{key}" not in signedurl response {mapping}')

        signed_url = mapping[key]

        with urlopen(Request(signed_url, None, {})) as response:
            if response.status != 200:
                raise ValueError(f"received {response.status} when accessing {url}")

            with open(directory / file, mode="wb") as handle:
                shutil.copyfileobj(response, handle)

        print(f"downloaded {file}")


if __name__ == "__main__":
    download(2015)
