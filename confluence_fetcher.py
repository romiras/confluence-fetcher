import os
import requests
import argparse
import re

def sanitize_directory_name(name):
    """Sanitizes a string to be a valid directory name."""
    # Remove invalid characters
    sanitized_name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Replace spaces with underscores
    sanitized_name = sanitized_name.replace(' ', '_')
    return sanitized_name

def get_spaces(account_name, user_email, api_token):
    """Fetches all spaces from the Confluence API."""
    base_url = f"https://{account_name}.atlassian.net/wiki/api/v2"
    url = f"{base_url}/spaces"
    auth = (user_email, api_token)
    headers = {
        "Accept": "application/json"
    }

    spaces = []
    while url:
        try:
            response = requests.get(url, headers=headers, auth=auth)
            response.raise_for_status()  # Raise an exception for bad status codes
            data = response.json()
            spaces.extend(data.get('results', []))
            next_path = data.get('_links', {}).get('next')
            if next_path:
                url = f"https://{account_name}.atlassian.net{next_path}"
            else:
                url = None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching spaces: {e}")
            return None
    return spaces

def main():
    """Main function to execute the script."""
    parser = argparse.ArgumentParser(description="Fetch Confluence spaces and create directories.")
    parser.add_argument("-a", "--accountname", required=True, help="Confluence account name.")
    parser.add_argument("-d", "--outputdir", required=True, help="Local output directory.")
    parser.add_argument("-s", "--spaces", help="Comma-separated list of space keys to fetch.")
    args = parser.parse_args()

    user_email = os.getenv("CONFL_USER_EMAIL")
    api_token = os.getenv("CONFL_API_TOKEN")
    if not api_token or not user_email:
        print("Error: CONFL_USER_EMAIL and CONFL_API_TOKEN environment variables must be set.")
        return

    print(f"Fetching spaces from {args.accountname}...")
    spaces = get_spaces(args.accountname, user_email, api_token)

    if spaces:
        if args.spaces:
            selected_space_keys = [key.strip() for key in args.spaces.split(',')]
            spaces = [s for s in spaces if s.get('key') in selected_space_keys]
            print(f"Filtering for spaces: {', '.join(selected_space_keys)}")

        print(f"Found {len(spaces)} spaces. Creating directories in {args.outputdir}...")
        os.makedirs(args.outputdir, exist_ok=True)
        for space in spaces:
            space_name = space.get('name', 'Untitled_Space')
            space_key = space.get('key', 'NO_KEY')
            sanitized_name = sanitize_directory_name(space_name)
            space_dir = os.path.join(args.outputdir, sanitized_name)
            os.makedirs(space_dir, exist_ok=True)
            print(f"  - Created directory for space: '{space_name}' (Key: {space_key}) -> {sanitized_name}")
        print("Done.")

if __name__ == "__main__":
    main()
