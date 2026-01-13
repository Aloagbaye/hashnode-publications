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
HASHNODE_API_KEY = os.getenv("HASHNODE_ACCESS_TOKEN")
if not HASHNODE_API_KEY:
    print("Error: HASHNODE_ACCESS_TOKEN environment variable is not set")
    sys.exit(1)


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
              domain {
                host
              }
            }
          }
        }
      }
    }
    """
    
    response = requests.post(
        HASHNODE_API_URL,
        json={"query": query},
        headers={
            "Authorization": HASHNODE_API_KEY,
            "Content-Type": "application/json"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if "data" in data and data["data"] and data["data"].get("me"):
            return data["data"]["me"]
    
    print(f"Error fetching user info: {response.text}")
    return None


def get_publication_id(domain: str) -> Optional[str]:
    """
    Get publication ID from domain using Hashnode API.
    """
    user_info = get_user_info()
    if not user_info:
        return None
    
    # Extract host from domain (remove https:// if present)
    host = domain.replace("https://", "").replace("http://", "").split("/")[0]
    
    # Find matching publication
    publications = user_info.get("publications", {}).get("edges", [])
    for pub_edge in publications:
        pub = pub_edge.get("node", {})
        pub_host = pub.get("domain", {}).get("host", "")
        if pub_host == host:
            return pub.get("id")
    
    print(f"Error: Publication with domain '{host}' not found")
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
            headers={
                "Authorization": HASHNODE_API_KEY,
                "Content-Type": "application/json"
            },
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
    domain = frontmatter.get("domain", "").strip()
    if not domain:
        print("   ⚠️  No domain specified in frontmatter, skipping")
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

