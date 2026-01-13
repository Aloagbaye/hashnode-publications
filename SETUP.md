# GitHub Workflow Setup for Hashnode Publishing

This repository includes an automated GitHub Actions workflow that publishes your markdown files to Hashnode.dev automatically.

## Setup Instructions

### 1. Get Your Hashnode API Key

1. Go to [Hashnode Settings](https://hashnode.com/settings/developer)
2. Navigate to the **Developer** section
3. Generate or copy your **Personal Access Token** (API Key)

### 2. Add GitHub Secret

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `HASHNODE_ACCESS_TOKEN`
5. Value: Paste your Hashnode API key
6. Click **Add secret**

### 3. Configure Your Markdown Files

Ensure each markdown file (except `README.md`) has the required frontmatter:

```yaml
---
title: "Your Post Title"
slug: your-post-slug
tags: tag1, tag2, tag3
domain: yourblog.hashnode.dev
---
```

**Required fields:**
- `title`: Post title
- `slug`: Unique URL slug
- `tags`: Comma-separated tags (max 5)
- `domain`: Your Hashnode publication domain

**Optional fields:**
- `subtitle`: Post subtitle
- `cover` or `cover_image`: Cover image URL
- `saveAsDraft`: Set to `true` to save as draft
- `hideFromHashnodeCommunity`: Set to `true` to hide from Hashnode feed
- `canonical`: Original article URL
- `seoTitle`: SEO title
- `seoDescription`: SEO description
- `disableComments`: Set to `true` to disable comments
- `seriesSlug`: Series slug
- `enableToc`: Set to `true` to enable table of contents
- `ignorePost`: Set to `true` to skip this post

### 4. How It Works

The workflow automatically:
- Triggers on push to `main` or `master` branch when `.md` files change
- Can be manually triggered from the **Actions** tab
- Detects changed/new markdown files (excluding `README.md`)
- Parses frontmatter and publishes to Hashnode
- Provides a summary of publishing results

### 5. Manual Trigger

You can manually trigger the workflow:
1. Go to **Actions** tab in your repository
2. Select **Publish to Hashnode** workflow
3. Click **Run workflow**
4. Select branch and click **Run workflow**

## Troubleshooting

- **"HASHNODE_ACCESS_TOKEN not set"**: Make sure you've added the secret in GitHub repository settings
- **"Publication not found"**: Verify the `domain` in your frontmatter matches your Hashnode publication domain
- **"Missing required fields"**: Ensure `title`, `slug`, `tags`, and `domain` are present in frontmatter
- Check the workflow logs in the **Actions** tab for detailed error messages

