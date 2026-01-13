#!/usr/bin/env python3
"""
Script to publish markdown files to Hashnode using their GraphQL API.
This script reads markdown files, parses frontmatter, and publishes them to Hashnode.
"""

import os
import re
import sys
import yaml
import json
import requests
from pathlib import Path
from typing import Dict, Optional, List, Tuple

# Hashnode GraphQL API endpoint
HASHNODE_API_URL = "https://gql.hashnode.com"

# Get API key from environment
HASHNODE_ACCESS_TOKEN = os.getenv("HASHNODE_ACCESS_TOKEN")
if not HASHNODE_ACCESS_TOKEN:
    print("Error: HASHNODE_ACCESS_TOKEN environment variable is not set")
    sys.exit(1)

# Format authorization header
# Hashnode API accepts the token directly (not with Bearer prefix)
HASHNODE_API_KEY = HASHNODE_ACCESS_TOKEN.strip()


def get_auth_headers() -> Dict[str, str]:
    """
    Get authorization headers for Hashnode API requests.
    """
    return {
        "Authorization": HASHNODE_API_KEY,
        "Content-Type": "application/json"
    }


def parse_frontmatter(content: str) -> Tuple[Optional[Dict], str]:
    """
    Parse YAML frontmatter from markdown content.
    Returns (frontmatter_dict, markdown_body)
    """
    # Match frontmatter between --- delimiters
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)
    
    if not match:
        return None, content
    
    frontmatter_str = match.group(1)
    markdown_body = match.group(2)
    
    try:
        frontmatter = yaml.safe_load(frontmatter_str)
        return frontmatter, markdown_body
    except yaml.YAMLError as e:
        print(f"Error parsing frontmatter: {e}")
        return None, content


def get_user_info() -> Optional[Dict]:
    """
    Get user information to retrieve publication details.
    """
    query = """
    query {
      me {
        id
        username
        publications(first: 10) {
          edges {
            node {
              id
              url
            }
          }
        }
      }
    }
    """
    
    try:
        response = requests.post(
            HASHNODE_API_URL,
            json={"query": query},
            headers=get_auth_headers(),
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "errors" in data:
                print(f"GraphQL Errors in get_user_info: {json.dumps(data['errors'], indent=2)}")
                return None
            
            if "data" in data and data["data"] and data["data"].get("me"):
                return data["data"]["me"]
        else:
            print(f"Error fetching user info: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        return None


def get_publication_id(domain: str) -> Optional[str]:
    """
    Get publication ID from domain using Hashnode API.
    Try two methods: from user's publications list, or direct publication query.
    """
    # Extract host from domain (remove https:// if present)
    host = domain.replace("https://", "").replace("http://", "").split("/")[0].strip()
    
    # Method 1: Get from user's publications list
    user_info = get_user_info()
    if user_info:
        publications = user_info.get("publications", {}).get("edges", [])
        print(f"Found {len(publications)} publication(s) for user")
        
        for pub_edge in publications:
            pub = pub_edge.get("node", {})
            pub_url = pub.get("url", "")
            # Extract host from URL (e.g., https://israelcodes.hashnode.dev -> israelcodes.hashnode.dev)
            if pub_url:
                pub_host = pub_url.replace("https://", "").replace("http://", "").split("/")[0].strip()
                
                # Try exact match first
                if pub_host.lower() == host.lower():
                    pub_id = pub.get("id")
                    print(f"✅ Found publication ID: {pub_id} for domain: {pub_host}")
                    return pub_id
                
                # Also try matching without .hashnode.dev suffix
                if host.endswith(".hashnode.dev"):
                    host_without_suffix = host.replace(".hashnode.dev", "")
                    pub_host_without_suffix = pub_host.replace(".hashnode.dev", "")
                    if host_without_suffix.lower() == pub_host_without_suffix.lower():
                        pub_id = pub.get("id")
                        print(f"✅ Found publication ID: {pub_id} for domain: {pub_host}")
                        return pub_id
        
        # Print available publications for debugging
        print(f"Available publications:")
        for pub_edge in publications:
            pub = pub_edge.get("node", {})
            pub_url = pub.get("url", "")
            if pub_url:
                pub_host = pub_url.replace("https://", "").replace("http://", "").split("/")[0]
                print(f"  - {pub_host} (ID: {pub.get('id')})")
    
    # Method 2: Try direct publication query
    print(f"Trying direct publication query for host: {host}")
    query = """
    query GetPublication($host: String!) {
      publication(host: $host) {
        id
        url
      }
    }
    """
    
    try:
        response = requests.post(
            HASHNODE_API_URL,
            json={"query": query, "variables": {"host": host}},
            headers=get_auth_headers(),
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "errors" in data:
                print(f"GraphQL Errors in get_publication_id: {json.dumps(data['errors'], indent=2)}")
            elif "data" in data and data["data"] and data["data"].get("publication"):
                pub_id = data["data"]["publication"]["id"]
                print(f"✅ Found publication ID via direct query: {pub_id}")
                return pub_id
    
    except requests.exceptions.RequestException as e:
        print(f"Error in direct publication query: {e}")
    
    print(f"❌ Error: Could not find publication with domain '{host}'")
    print(f"   Searched for: {host}")
    return None


def get_existing_post_id(publication_id: str, slug: str) -> Optional[str]:
    """
    Check if a post with the given slug already exists.
    """
    query = """
    query GetPost($slug: String!, $host: String!) {
      post(slug: $slug, host: $host) {
        id
      }
    }
    """
    
    # Extract host from publication_id or use a different approach
    # For now, we'll try to get it from the domain in frontmatter
    # This is a simplified version - you may need to adjust based on your setup
    
    return None  # Simplified - will create new post or update based on slug


def publish_post(frontmatter: Dict, content: str, domain: str) -> bool:
    """
    Publish a post to Hashnode using GraphQL API.
    """
    # Get publication ID
    publication_id = get_publication_id(domain)
    if not publication_id:
        print(f"Error: Could not get publication ID for domain {domain}")
        return False
    
    # Extract required fields
    title = frontmatter.get("title", "").strip('"').strip("'")
    slug = frontmatter.get("slug", "")
    tags = frontmatter.get("tags", "")
    
    if not title or not slug:
        print(f"Error: Missing required fields (title or slug)")
        return False
    
    # Parse tags (can be comma-separated string or list)
    if isinstance(tags, str):
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
    elif isinstance(tags, list):
        tag_list = [str(tag).strip() for tag in tags if tag]
    else:
        tag_list = []
    
    # Limit to 5 tags as per Hashnode requirements
    tag_list = tag_list[:5]
    
    # Build mutation - using Hashnode's actual API structure
    mutation = """
    mutation PublishPost($input: PublishPostInput!) {
      publishPost(input: $input) {
        post {
          id
          slug
          url
          title
          publishedAt
        }
        success
      }
    }
    """
    
    # Build input object according to Hashnode API
    input_data = {
        "publicationId": publication_id,
        "title": title,
        "slug": slug,
        "contentMarkdown": content
    }
    
    # Add tags if provided
    if tag_list:
        input_data["tags"] = [{"slug": tag, "name": tag} for tag in tag_list]
    
    # Add optional fields
    if "subtitle" in frontmatter and frontmatter["subtitle"]:
        input_data["subtitle"] = str(frontmatter["subtitle"]).strip('"').strip("'")
    
    if "cover" in frontmatter and frontmatter["cover"]:
        input_data["coverImageURL"] = str(frontmatter["cover"]).strip()
    elif "cover_image" in frontmatter and frontmatter["cover_image"]:
        input_data["coverImageURL"] = str(frontmatter["cover_image"]).strip()
    
    # Handle publish status
    if frontmatter.get("saveAsDraft", False):
        input_data["publishStatus"] = "DRAFT"
    else:
        input_data["publishStatus"] = "PUBLISHED"
    
    if frontmatter.get("hideFromHashnodeCommunity", False):
        input_data["hideFromHashnodeCommunity"] = True
    
    if "canonical" in frontmatter and frontmatter["canonical"]:
        input_data["originalArticleURL"] = str(frontmatter["canonical"]).strip()
    
    if "seoTitle" in frontmatter and frontmatter["seoTitle"]:
        input_data["seoTitle"] = str(frontmatter["seoTitle"]).strip('"').strip("'")
    
    if "seoDescription" in frontmatter and frontmatter["seoDescription"]:
        input_data["seoDescription"] = str(frontmatter["seoDescription"]).strip('"').strip("'")
    
    if frontmatter.get("disableComments", False):
        input_data["disableComments"] = True
    
    if "seriesSlug" in frontmatter and frontmatter["seriesSlug"]:
        input_data["seriesSlug"] = str(frontmatter["seriesSlug"]).strip()
    
    if frontmatter.get("enableToc", False):
        input_data["enableTableOfContents"] = True
    
    variables = {"input": input_data}
    
    # Make API request
    try:
        response = requests.post(
            HASHNODE_API_URL,
            json={"query": mutation, "variables": variables},
            headers=get_auth_headers(),
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "errors" in data:
                print(f"GraphQL Errors: {json.dumps(data['errors'], indent=2)}")
                return False
            
            if "data" in data and data["data"] and data["data"].get("publishPost"):
                publish_result = data["data"]["publishPost"]
                if publish_result.get("success"):
                    post = publish_result.get("post", {})
                    print(f"✅ Successfully published: {post.get('title', title)}")
                    if post.get("url"):
                        print(f"   URL: {post['url']}")
                    elif post.get("slug"):
                        print(f"   Slug: {post['slug']}")
                    return True
                else:
                    print(f"❌ Publishing failed (success: false)")
                    return False
        else:
            print(f"Error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        return False


def process_markdown_file(file_path: Path) -> bool:
    """
    Process a single markdown file and publish it to Hashnode.
    """
    print(f"\n📄 Processing: {file_path}")
    
    # Skip README.md and SETUP.md
    if file_path.name == "README.md":
        print("   ⏭️  Skipping README.md")
        return False
    
    if file_path.name == "SETUP.md":
        print("   ⏭️  Skipping SETUP.md")
        return False
    
    # Read file
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"   ❌ Error reading file: {e}")
        return False
    
    # Parse frontmatter
    frontmatter, markdown_body = parse_frontmatter(content)
    
    if not frontmatter:
        print("   ⚠️  No frontmatter found, skipping")
        return False
    
    # Check if post should be ignored
    if frontmatter.get("ignorePost", False):
        print("   ⏭️  Post marked to be ignored (ignorePost: true)")
        return False
    
    # Get domain (required)
    domain_value = frontmatter.get("domain")
    if domain_value is None:
        print("   ⚠️  No domain specified in frontmatter, skipping")
        return False
    
    # Handle both string and None cases
    domain = str(domain_value).strip() if domain_value else ""
    if not domain:
        print("   ⚠️  Domain is empty in frontmatter, skipping")
        return False
    
    # Publish post
    return publish_post(frontmatter, markdown_body, domain)


def main():
    """
    Main function to process all markdown files.
    """
    results = []
    
    # Get list of markdown files to process
    # Check if changed_files.txt exists (from GitHub Actions)
    changed_files_path = Path("changed_files.txt")
    if changed_files_path.exists():
        with open(changed_files_path, "r") as f:
            file_list = [line.strip() for line in f if line.strip()]
    else:
        # Fallback: process all .md files in root (except README.md and SETUP.md)
        file_list = [str(f) for f in Path(".").glob("*.md") if f.name not in ["README.md", "SETUP.md"]]
    
    if not file_list:
        print("No markdown files to process")
        return
    
    print(f"Found {len(file_list)} markdown file(s) to process")
    
    # Process each file
    for file_path_str in file_list:
        file_path = Path(file_path_str)
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue
        
        success = process_markdown_file(file_path)
        results.append({
            "file": file_path_str,
            "success": success
        })
    
    # Write results summary
    with open("publish_results.txt", "w") as f:
        f.write("### Publishing Results\n\n")
        for result in results:
            status = "✅ Success" if result["success"] else "❌ Failed"
            f.write(f"- {status}: `{result['file']}`\n")
    
    # Exit with error if any failed
    if any(not r["success"] for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()

