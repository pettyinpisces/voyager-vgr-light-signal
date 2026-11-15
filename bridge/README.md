# VGR Bridge reference implementation

This directory contains a deliberately narrow local controller for one Philips
Hue light named `VGR`. It sends one complete `...- --. .-.` transmission, keeps
separate run counts for fixed actors, rejects overlapping runs, supports an
emergency stop, and restores the light's earlier state.

The Hue Bridge and application key remain on this computer. Do not expose the
raw Hue API to the public internet.

## Requirements

- macOS, Windows, Linux, or Raspberry Pi OS
- Python 3.10 or later
- A Philips Hue Bridge and one Hue light with the unique name `VGR`
- The computer and Bridge on the same local network
- Claude Desktop only if using the included local MCP path

The command-line controller uses only Python's standard library. The MCP server
also needs the package listed in `requirements.txt`.

## 1. Create an isolated environment

macOS or Linux:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 2. Pair locally

Press the large round button on the Hue Bridge, then run this within the short
pairing window:

```sh
python vgr_cli.py pair <bridge-address> --light-name VGR
```

This writes `config.json` with owner-only permissions. The file contains the
private application key and is ignored by Git. Pairing also creates these
generic actors:

```text
companion-a
companion-b
human
```

You may change `allowed_actors` in the private `config.json`. Use short,
non-secret labels. An MCP launcher's `VGR_ACTOR` must exactly match one label.

## 3. Run inert checks

These commands do not change the light:

```sh
python vgr_cli.py plan
python vgr_cli.py check
python -m unittest discover -s tests -v
```

`check` refuses to continue unless exactly one Bridge light matches the
configured name.

## 4. Rehearse manually

Arm one run for one actor:

```sh
python vgr_cli.py arm --actors companion-a --minutes 10 --runs-each 1
```

Start a video recording of reflected light, then transmit:

```sh
python vgr_cli.py transmit companion-a
```

Inspect the video for `...- --. .-.`, confirm the light restored, and disarm:

```sh
python vgr_cli.py disarm
```

Emergency stop is always available:

```sh
python vgr_cli.py stop
```

## 5. Give a companion a fixed identity

Copy one launcher from `launchers/`, remove the `.example` suffix, replace the
placeholder absolute paths, and make it executable on macOS or Linux:

```sh
chmod 700 launchers/run-vgr-companion-a.command
```

The launcher—not model input—sets `VGR_ACTOR`. Give each companion a different
launcher. Do not provide a tool that accepts a free-form actor name.

### Claude Desktop

The manual configuration entry is:

```json
{
  "mcpServers": {
    "vgr-companion-a": {
      "command": "/absolute/path/to/run-vgr-companion-a.command",
      "args": []
    }
  }
}
```

Merge that entry into the existing `mcpServers` object. Do not erase other
servers. The optional installer makes a timestamped backup and performs that
merge:

```sh
python install_claude_bridge.py \
  --server-name vgr-companion-a \
  --command /absolute/path/to/run-vgr-companion-a.command
```

Fully quit and reopen Claude Desktop. Confirm that it exposes only:

```text
vgr_status
transmit_vgr
stop_vgr
```

Call `vgr_status` while disarmed before any live test. For a transmission,
select **Allow once**, not permanent approval.

### ChatGPT and OpenAI surfaces

Do not paste the Claude stdio configuration into ChatGPT and assume it will
work. Use an approved local desktop integration, authenticated private MCP
connection, or trusted local automation host. The outer connection may differ;
the fixed launcher, local human arming, one-run accounting, narrow tools, and
emergency stop remain the same.

## Files created at runtime

```text
config.json                  private Hue address and application key
runtime/armed.json           short-lived expiration and remaining runs
runtime/transmission.lock    operating-system lock target
runtime/transmissions.jsonl  sanitized completion records
runtime/STOP                 cross-process emergency-stop signal
```

None of these files belongs in a public repository or support screenshot.

## Known boundaries

- The reference Hue client uses local API v1 resources.
- The local Bridge certificate is device-local, so this narrowly scoped client
  does not validate it against the public certificate-authority store.
- This is event-oriented reference code, not a general smart-home controller.
- The companion cannot arm itself, select another actor, choose arbitrary
  lights, or send raw Hue commands.

## License

Code in this directory is licensed under the repository's `LICENSE-CODE` MIT
license.

