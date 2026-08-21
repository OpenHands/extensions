---
name: slack-responder
description: Set up an automated Slack responder that monitors channels for engineering questions and requests, then responds with helpful information or takes action on behalf of the team.
triggers:
- /slack-responder
- /setup-slack-bot
---

# Slack Responder

Create an automated engineering assistant that monitors Slack and responds to requests.

## Process

1. **Configure monitoring**: Set up channels and trigger phrases
2. **Define responses**: Map requests to actions or information
3. **Implement automation**: Create the polling and response workflow
4. **Test and deploy**: Verify the bot works correctly

## Use Cases

### Engineering Support
- Answer common questions about the codebase
- Provide links to relevant documentation
- Explain how features work

### Request Handling
- Respond to @openhands mentions
- Handle on-call handoffs
- Triage incoming requests

### Automated Actions
- Trigger deployments
- Create tickets from messages
- Generate reports on request

## Setup Steps

### 1. Slack App Configuration
- Create a Slack app with appropriate permissions
- Add bot token scopes: `channels:history`, `chat:write`
- Install to workspace

### 2. Channel Monitoring
- Select channels to monitor
- Configure trigger phrases (e.g., "@openhands", "help:")
- Set polling interval

### 3. Response Configuration
- Define response templates
- Configure which actions to take
- Set up escalation paths

### 4. Automation Setup
- Create a cron automation in OpenHands
- Configure the Slack channel monitor skill
- Test with sample messages

## Integration with OpenHands

Use the `slack-channel-monitor` skill to:
- Poll up to 10 Slack channels
- Detect trigger phrases
- Start OpenHands conversations for complex requests
- Post responses back to Slack

See the [Slack Channel Monitor](https://github.com/OpenHands/extensions/tree/main/skills/slack-channel-monitor) skill for detailed setup instructions.
