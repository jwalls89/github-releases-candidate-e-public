---
description: Review PR comments one-by-one and resolve them interactively
---

# PR Review Command

Review all PR comments for the current branch, one at a time, and help resolve them.

This includes:
- **Review thread comments** - line-attached code review comments (can be resolved)
- **Regular PR comments** - general conversation comments (replied to but not resolvable)

## Instructions

### Step 1: Find the PR

Run this command to check if there's a PR for the current branch:

```bash
gh pr view --json number,url,state
```

**If no PR exists:** Tell the user "No PR found for the current branch. Create one with `gh pr create`" and stop.

**If PR is closed/merged:** Tell the user "PR is already closed/merged" and stop.

### Step 2: Fetch All Comments

There are two types of PR comments to fetch:

#### 2a. Review Comments (line-attached)

These are comments attached to specific lines in the diff:

```bash
gh api repos/{owner}/{repo}/pulls/{number}/comments
```

Extract: `id`, `path`, `line`, `body` for each comment.

#### 2b. Regular PR Comments (conversation)

These are general comments on the PR not attached to specific lines:

```bash
gh pr view {number} --json comments --jq '.comments'
```

Extract: `id`, `author`, `body`, `createdAt` for each comment.

### Step 3: Get Thread Resolution Status

Get the thread IDs and check which are unresolved:

```bash
gh api graphql -f query='query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          comments(first: 1) {
            nodes {
              path
              line
            }
          }
        }
      }
    }
  }
}' -f owner='{owner}' -f repo='{repo}' -F pr={number}
```

Match comments to threads by path and line number to determine which are unresolved.

**If all review thread comments are resolved AND no regular PR comments exist:** Tell the user "All review comments are already resolved!" and stop.

**If no comments exist (neither review nor regular):** Tell the user "No comments found on this PR" and stop.

### Step 4: Process Each Comment

Process comments in this order:
1. **Unresolved review thread comments** (line-attached) - these have path/line context
2. **Regular PR comments** (conversation) - these are general feedback without line context

#### For Review Thread Comments:

For each unresolved comment, do the following:

#### 4a. Display the Comment

```
---

## Comment X of Y: [Brief description based on comment content]

**File:** `[path]`
**Line:** [line number]

**Comment:**
> [The full comment body]
```

#### 4b. Read the Relevant Code

Use the Read tool to read the file mentioned in the comment, focusing on the relevant lines. This gives you context to assess the comment.

#### 4c. Provide Your Assessment

**CRITICAL:** Before agreeing with any factual claims, VERIFY them:
- If reviewer says "directory X doesn't exist" → check if it exists
- If reviewer says "version Y isn't released" → search the web to verify
- If reviewer says "flag Z requires flag W" → check the documentation

Then provide your assessment:

```
**My Assessment:** [Agree/Disagree] - [Should fix / Won't fix]

[Your reasoning, including any verification you did]
```

#### 4d. Ask the User What To Do

Ask the user:
```
What would you like to do?
1. Fix it (I'll make the change and update tests if needed)
2. Won't fix (I'll reply with the reason and resolve)
3. Skip (move to next comment without action)
```

**WAIT for the user's response before proceeding.**

#### 4e. Execute the User's Choice

**If "Fix it":**
1. Make the code change using the Edit tool
2. Search for related tests: `grep -r "function_name" tests/` or similar
3. Update tests if they exist and are affected
4. Reply to the comment on GitHub:
   ```bash
   gh api repos/{owner}/{repo}/pulls/{pull_number}/comments -f body="Fixed: [brief description of what was changed]" -F in_reply_to_id={comment_id}
   ```
5. Resolve the thread:
   ```bash
   gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "[thread_id]"}) { thread { isResolved } } }'
   ```

**If "Won't fix":**
1. Ask the user for the reason (or use your assessment reasoning)
2. Reply to the comment on GitHub:
   ```bash
   gh api repos/{owner}/{repo}/pulls/{pull_number}/comments -f body="Won't fix: [reason]" -F in_reply_to_id={comment_id}
   ```
3. Resolve the thread (same GraphQL mutation as above)

**If "Skip":**
1. Move to the next comment without any action

#### For Regular PR Comments:

Regular PR comments don't have thread resolution status - they're general conversation comments. Process each one similarly:

##### Display the Comment

```
---

## PR Comment X of Y: [Brief description based on comment content]

**Author:** [author login]
**Posted:** [createdAt]

**Comment:**
> [The full comment body]
```

##### Assess and Ask

Follow the same assessment process (4c) and ask the user (4d) what to do.

##### Execute the Choice

**If "Fix it":**
1. Make the changes as requested
2. Reply to the comment:
   ```bash
   gh pr comment {number} --body "Fixed: [brief description of what was changed]"
   ```

**If "Won't fix":**
1. Reply with the reason:
   ```bash
   gh pr comment {number} --body "Won't fix: [reason]"
   ```

**If "Skip":**
1. Move to the next comment without any action

**Note:** Regular PR comments don't have a "resolve" mechanism like review threads - replying is sufficient.

### Step 5: Summary

After all comments are processed, show a summary:

```
---

## Summary

| Comment Type | Fixed | Won't Fix | Skipped |
|--------------|-------|-----------|---------|
| Review threads | X | Y | Z |
| PR comments | A | B | C |

[If any fixes were made:]
You have uncommitted changes. Would you like me to commit them?
```

## Important Rules

1. **One comment at a time** - Never batch or skip ahead
2. **Always verify claims** - Don't trust reviewer assertions without checking
3. **Wait for user input** - After presenting each comment, wait for the user's decision
4. **Update tests** - When fixing code, always check for and update related tests
5. **Use exact GitHub API commands** - The commands above are tested and work

## Error Handling

- If `gh` commands fail, check if user is authenticated: `gh auth status`
- If GraphQL queries fail, the repo owner/name might be wrong - extract from `gh repo view --json owner,name`
