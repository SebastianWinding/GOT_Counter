import random
import sqlite3
import time
import requests

DB_PATH = "assets/shows.db"
API_URL = "https://graphql.anilist.co"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS anime (
            id INTEGER PRIMARY KEY,
            title_romaji TEXT,
            title_english TEXT,
            synonyms TEXT,
            start_year INTEGER,
            season TEXT,
            format TEXT,
            cover_image TEXT
        )
    ''')
    conn.commit()
    return conn


def anime_exists(conn, anime_id):
    c = conn.cursor()
    c.execute("SELECT 1 FROM anime WHERE id = ?", (anime_id,))
    return c.fetchone() is not None


def store_anime(conn, anime):
    c = conn.cursor()
    c.execute('''
        INSERT INTO anime (
            id, title_romaji, title_english, synonyms,
            start_year, season, format, cover_image
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        anime["id"],
        anime["title"].get("romaji"),
        anime["title"].get("english"),
        ", ".join(anime.get("synonyms", [])),
        anime["startDate"].get("year"),
        anime.get("season"),
        anime.get("format"),
        anime["coverImage"].get("large") or anime["coverImage"].get("extraLarge")
    ))
    conn.commit()


def fetch_anime_page(page):
    query = '''
    query($page: Int, $type: MediaType, $format: [MediaFormat], $sort: [MediaSort]) {
      Page(page: $page, perPage: 50) {
        media(
          type: $type,
          format_in: $format,
          sort: $sort
        ) {
          id
          title {
            romaji
            english
          }
          synonyms
          startDate {
            year
            month
            day
          }
          season
          format
          coverImage {
            large
            extraLarge
          }
        }
      }
    }
    '''
    variables = {
        "page": page,
        "type": "ANIME",
        "format": ["TV", "MOVIE", "TV_SHORT"],
        "sort": ["ID_DESC"]
    }

    attempt = 0
    max_attempts = 5

    while True:
        try:
            response = requests.post(
                API_URL,
                json={"query": query, "variables": variables},
                timeout=10
            )

            if response.status_code == 429:
                wait_time = 62 + random.uniform(0, 5)
                print(f"Rate limited (429), retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
                attempt = 0  # reset on 429
                continue

            response.raise_for_status()
            return response.json()["data"]["Page"]["media"]

        except requests.RequestException as e:
            attempt += 1
            if attempt > max_attempts:
                raise Exception(f"Failed after {max_attempts} retries: {e}")
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            print(f"Request error: {e}, retrying in {wait_time:.2f}s...")
            time.sleep(wait_time)


def sync():
    conn = init_db()
    page = 1
    total_inserted = 0

    while True:
        animes = fetch_anime_page(page)
        if not animes:
            break

        for anime in animes:
            if anime_exists(conn, anime["id"]):
                print(f"Duplicate found: {anime['id']} — stopping update.")
                conn.close()
                return
            store_anime(conn, anime)
            total_inserted += 1
            print(f"Inserted anime {anime['id']} - {anime['title']['romaji']}")

        page += 1

    conn.close()
    print(f"Update complete. Inserted {total_inserted} new entries.")


if __name__ == "__main__":
    sync()
