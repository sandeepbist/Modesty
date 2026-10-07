# Security and privacy

Only the current `main` branch receives fixes. Modesty runs with your desktop
user's access; installing it changes desktop configuration and may install system
packages. It is not a security boundary around applications running on your PC.

## Report a vulnerability

Use **Security → Report a vulnerability** for a private report when that feature
is enabled on the public repository. If the button is unavailable, open an issue
asking the maintainer for a private reporting route without including exploit
details or sensitive data. Never post keys, passwords or private logs publicly.
Include the affected revision, impact and minimal reproduction in the private
report. The maintainer reviews reports; there is no guaranteed response deadline.

## Luma

Speech recognition runs locally. AI answers use a cloud provider configured by
the user. Submitted text, enabled window context, relevant file/document excerpts
and tool results can be sent to that provider. Do not enable context or knowledge
folders whose contents you do not want shared. Provider usage may incur charges.

API keys are stored outside the checkout with owner-only file permissions. Known
key, browser, keyring and common credential locations are excluded from file
tools. Generic commands require confirmation in the default Review mode, even
when read-only. Their default bubblewrap environment has read-only files,
separate process/network namespaces and hidden known credential locations.
Unknown credential locations are not guaranteed to be hidden. Review the exact
command and requested access before approving it.

Approved writable, network and session flags expand access. Privileged commands
use native `pkexec` authentication. Full access allows automatic actions and
should only be enabled deliberately. Model output and permission classification
are not proof that an action is safe or correct.

## Local integrations

The privacy panel observes capture metadata and offers microphone mute controls;
it does not revoke every application's device permissions. Companion typing
reactions use activity events rather than recording typed characters. T3 Code
integration reads task status metadata, not prompts or credentials. Standalone
agent CLI tracking is not implemented.

Installation templates exclude conversations, personal knowledge, keys and model
caches. Review local changes before publishing your own fork. Research notes and
temporary outputs are ignored. Fork CI receives no project secrets and uses
read-only repository permissions.
