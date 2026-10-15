# TurnShade

Chrome extension that makes turn-taking in vertically split ChatGPT conversations easier to follow.

- Sending a message shades the sending ChatGPT pane.
- The opposite pane becomes unshaded so the next turn is obvious.
- Includes a popup for diagnostics, manual shading, and reset.
- Works with Chrome's native Split View; an optional two-tab fallback is available.

## Installing

Use the built extension ZIP from [Actions](../../actions/workflows/package.yml): download the workflow's artifact, extract the inner `turnshade-vX.Y.Z.zip`, then load the extracted folder from `chrome://extensions` using **Load unpacked**. Both ChatGPT tabs must be reloaded after installation.

## Continuous integration

On each push to `master`, `.github/workflows/package.yml` validates the extension and creates `turnshade-v<manifest.version>.zip` containing only:

- `manifest.json`
- `service-worker.js`, `content.js`, `popup.js`, `popup.html`
- `icons/icon16.png`, `icons/icon48.png`, `icons/icon128.png`

The artifact is retained for up to 90 days. The workflow can also be run manually. Releases and Chrome Web Store publication are not automated.

The initial repository setup requires the extension source and image assets to be committed to `master` before CI can produce the ZIP.

## Development

```sh
node --test tests/service-worker.test.cjs
```

The browser DOM smoke test at `tests/content-browser-check.py` requires local Playwright and Chromium; it is not a logged-in ChatGPT end-to-end test.
