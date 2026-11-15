# Security policy

## Never publish live household values

Do not commit or attach any of the following:

- `bridge/config.json`
- Anything under `bridge/runtime/`
- A Hue Bridge address, Bridge ID, application key, or exact light resource ID
- Account IDs, passwords, cookies, OAuth tokens, recovery codes, or tunnel URLs
- Personal names not intentionally included in the public credits
- Home, room, network, device, or camera names
- Private absolute filesystem paths or computer usernames

Use `bridge/config.example.json` and the launcher examples as templates.

## If a Hue application key is exposed

Remove the public value, revoke that application's Hue access, press the
physical Bridge button, create a new application key, and update only the
private local configuration. Removing a secret from the current branch does
not remove it from Git history; treat every committed key as compromised.

## Reporting a vulnerability

Until a dedicated security contact is published, do not open a public issue
containing household data or credentials. Contact the repository owner
privately through the account listed on the repository profile.

