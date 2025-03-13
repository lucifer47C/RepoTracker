import os
import asyncio
import aiohttp
import datetime
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

if not GITHUB_TOKEN or not GITHUB_USERNAME:
    raise ValueError("[ERROR] GitHub credentials are missing. Set GITHUB_TOKEN and GITHUB_USERNAME in the environment.")

GITHUB_API_URL = f"https://api.github.com/users/{GITHUB_USERNAME}/repos?per_page=100&type=all&page="

# Output directories
TEXT_FOLDER = "output/text"
MARKDOWN_FOLDER = "output/markdown"
LOGS_FOLDER = "logs"

# Logging setup
LOG_FILE = f"{LOGS_FOLDER}/log.txt"
os.makedirs(LOGS_FOLDER, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def log_message(message):
    """Log a message with a timestamp."""
    logging.info(message)
    print(f"[LOG] {message}")

def check_folders():
    """Ensure necessary folders exist."""
    for folder in [TEXT_FOLDER, MARKDOWN_FOLDER]:
        os.makedirs(folder, exist_ok=True)
        log_message(f"[INFO] Folder checked: {folder}")

async def check_rate_limit():
    """Check GitHub API rate limits and wait if necessary."""
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.github.com/rate_limit", headers=headers) as response:
            if response.status != 200:
                log_message(f"[ERROR] Failed to fetch rate limit: {response.status}")
                return
            data = await response.json()
            remaining = data['rate']['remaining']
            reset_time = datetime.datetime.fromtimestamp(data['rate']['reset'])
            if remaining == 0:
                wait_time = (reset_time - datetime.datetime.now()).total_seconds()
                log_message(f"[WAIT] Rate limit exceeded. Waiting {wait_time:.2f} seconds...")
                await asyncio.sleep(wait_time)

async def fetch_repos():
    """Fetch GitHub repositories asynchronously."""
    log_message("[INFO] Fetching repositories from GitHub...")
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    repos = []
    page = 1

    async with aiohttp.ClientSession() as session:
        while True:
            await check_rate_limit()
            async with session.get(GITHUB_API_URL + str(page), headers=headers) as response:
                if response.status != 200:
                    log_message(f"[ERROR] Failed to fetch repositories. Status Code: {response.status}")
                    return []
                page_repos = await response.json()
                if not page_repos:
                    break
                repos.extend(page_repos)
                page += 1

    log_message(f"[SUCCESS] Retrieved {len(repos)} repositories.")
    return repos

def format_repo_list(repos):
    """Format and save repository details in text and markdown."""
    total_repos = len(repos)
    public_repos = sum(1 for repo in repos if not repo["private"])
    private_repos = total_repos - public_repos
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    text_filename = f"{TEXT_FOLDER}/text_output_{timestamp}.txt"
    markdown_filename = f"{MARKDOWN_FOLDER}/markdown_output_{timestamp}.md"

    log_message("[INFO] Formatting repository data...")
    header_text = f"GitHub Inventory Report\nTotal Repositories: {total_repos}\nPublic Repos: {public_repos}\nPrivate Repos: {private_repos}\n\n"
    header_markdown = f"# GitHub Inventory Report\n**Total Repositories:** {total_repos}\n**Public Repos:** {public_repos}\n**Private Repos:** {private_repos}\n\n"
    text_output = header_text
    markdown_output = header_markdown

    for index, repo in enumerate(repos, 1):
        name = repo["name"]
        desc = repo["description"] or "No description provided."
        visibility = "Public" if not repo["private"] else "Private"
        repo_link = repo["html_url"]

        text_output += f"{index}. {name} ({visibility})\n  {desc}\n\n"
        markdown_output += f"### {index}. [{name}]({repo_link}) ({visibility})\n{desc}\n\n"

    with open(text_filename, "w", encoding="utf-8") as text_file:
        text_file.write(text_output)
    log_message(f"[SAVED] Text report generated: {text_filename}")

    with open(markdown_filename, "w", encoding="utf-8") as markdown_file:
        markdown_file.write(markdown_output)
    log_message(f"[SAVED] Markdown report generated: {markdown_filename}")

def main():
    """Main execution function."""
    check_folders()
    log_message("🔹 Starting GitHub Inventory Tool 🔹")
    repos = asyncio.run(fetch_repos())
    if repos:
        format_repo_list(repos)
    log_message("✅ Done. Exiting program.")

if __name__ == "__main__":
    main()
