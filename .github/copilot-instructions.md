# Agentic Experiences Repository

This repository documents and shares experiences with AI agents, coding
assistants, and related agentic technologies. It serves as a knowledge base
of real-world examples, scenarios, and outcomes from various AI agent
interactions.

Always reference these instructions first and fallback to search or bash
commands only when you encounter unexpected information that does not match
the info here.

## Working Effectively

### Repository Setup and Navigation

- Clone and navigate to repository:
  - `git clone https://github.com/falkorichter/agentic-experiences.git`
  - `cd agentic-experiences`

- Install required tools for markdown validation:
  - `npm install markdownlint-cli --global` -- takes 20-30 seconds. NEVER CANCEL.

- Validate current markdown content:
  - `markdownlint README.md` -- takes less than 1 second
  - Run with relaxed rules: `markdownlint README.md --disable MD013 MD031 MD040`

### Repository Structure

- `README.md` - Main documentation file containing all agentic experiences
- `LICENSE` - Apache 2.0 license file
- `.github/` - GitHub configuration and this instructions file

### Content Organization

The README.md is organized with sections covering:

- Android debugging scenarios and solutions
- GitHub Copilot web experiences and examples
- AI agent building resources and links
- Shell scripting examples and fixes
- Various AI interaction scenarios and outcomes

## Validation

### Markdown Validation

- ALWAYS run markdown linting before committing changes:
  - `markdownlint README.md` for strict validation
  - `markdownlint README.md --disable MD013 MD031 MD040` for relaxed validation (recommended)

- Common markdown issues to watch for:
  - Long lines (>80 characters) - use MD013 disable if needed
  - Missing language tags in code blocks - add language identifiers
  - Hard tabs - replace with spaces
  - Trailing spaces - remove them
  - Multiple consecutive blank lines - limit to single blank lines

### Content Validation

- Verify all URLs are accessible when adding new links
- Test any shell scripts or code examples before documenting them
- Ensure new content fits the repository's theme of agentic experiences
- Check that formatting is consistent with existing content

### Git Workflow Validation

- Always check git status before committing: `git status`
- Review changes before committing: `git diff`
- Use descriptive commit messages that explain the new content added

## Common Tasks

### Adding New Agentic Experiences

- Add new sections to README.md following the existing pattern
- Include relevant links, code examples, and context
- Document both successful and failed attempts for learning purposes
- Add timestamps or dates when relevant for historical context

### Updating Existing Content

- Preserve original content when making updates
- Add notes about updates or corrections rather than completely replacing content
- Maintain the chronological flow of experiences

### Link Management

- Verify external links work before adding them
- Use descriptive link text rather than bare URLs when possible
- Document any access restrictions or authentication requirements for links

## Repository Purpose and Key Areas

### Main Content Areas

1. **Android Debugging** - Runtime exceptions, manifest issues, SDK problems
2. **GitHub Copilot Web** - Browser-based coding experiences and limitations
3. **AI Agent Building** - Resources and frameworks for creating agents
4. **Shell Scripting** - Examples of AI-assisted script creation and debugging
5. **General AI Interactions** - Various scenarios and outcomes

### Frequently Referenced Content

- Android manifest troubleshooting examples (lines 1-80)
- GitHub Copilot session links and analyses (lines 90-130)
- Agent building resources and frameworks (lines 120-140)
- Shell script debugging examples (lines 180-235)

### Content Quality Guidelines

- Document both successful and unsuccessful AI interactions
- Include enough context for others to understand the scenario
- Preserve error messages and debugging output exactly as they occurred
- Link to external resources like session recordings or artifacts when available

## Time Expectations and Commands

### Quick Operations (< 5 seconds)

- `git status` and `git diff` - instant
- `markdownlint README.md` - takes ~0.3 seconds
- File viewing and editing operations - instant

### Standard Operations (5-30 seconds)

- `npm install markdownlint-cli --global` - takes 20-30 seconds. NEVER CANCEL.
- Git operations like `git add`, `git commit`, `git push` - takes 5-15 seconds

### No Build Process

- This repository has NO build process - it's documentation only
- NO compilation, bundling, or deployment steps required
- NO test suites to run - validation is limited to markdown linting

## Critical Reminders

- This is a DOCUMENTATION repository - no code compilation or execution
- Focus on markdown quality and content organization
- Preserve historical context of AI agent interactions
- ALWAYS validate markdown before committing changes
- NEVER delete existing experiences - only add or annotate them
