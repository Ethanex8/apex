# Portable GitHub PR `gh` Recipes

Use these commands in repositories that do not ship custom PR helper scripts (`scripts/harvest_feedback.py`, `scripts/watch_pr_feedback.py`).

## 1. Harvest Unresolved Review Threads (GraphQL)

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          nodes {
            id
            isResolved
            path
            line
            comments(first: 20) {
              nodes { databaseId author { login } body createdAt }
            }
          }
        }
      }
    }
  }' -F owner="{owner}" -F repo="{repo}" -F pr=<N> \
  --jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)'
```

## 2. Harvest Top-Level Reviews & Issue Comments

```bash
gh api repos/{owner}/{repo}/pulls/<N>/reviews --paginate
gh api repos/{owner}/{repo}/issues/<N>/comments --paginate
```

## 3. Acknowledge Picked-Up Comments (`eyes` Reaction)

```bash
# Inline PR review comment
gh api -X POST repos/{owner}/{repo}/pulls/comments/<comment_id>/reactions -f content=eyes

# Top-level issue/PR conversation comment
gh api -X POST repos/{owner}/{repo}/issues/comments/<comment_id>/reactions -f content=eyes
```

## 4. Reply Across Channels (Without Auto-Resolving)

```bash
# Reply inside an inline review thread
gh api -X POST repos/{owner}/{repo}/pulls/<N>/comments/<root_comment_id>/replies \
  -f body="🤖 [Antigravity] Fixed in <sha> — <short summary>."

# Reply to a top-level PR conversation or review summary
gh api -X POST repos/{owner}/{repo}/issues/<N>/comments \
  -f body="🤖 [Antigravity] Updated in <sha> — <short summary>."
```
