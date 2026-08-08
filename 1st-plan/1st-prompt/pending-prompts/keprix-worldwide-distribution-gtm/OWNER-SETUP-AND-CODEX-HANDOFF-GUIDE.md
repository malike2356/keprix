# Owner setup and Codex handoff guide

**Status:** OWNER ACTION REQUIRED
**Updated:** 2026-08-08
**Repository:** `malike2356/keprix`

This guide covers everything the owner must configure before Codex can publish,
verify, and finish the Keprix worldwide release programme. Complete the sections
in order. Never paste passwords, tokens, certificate files, private keys, recovery
codes, or secret values into chat, issues, commits, screenshots, or documentation.

## 1. Understand the boundary

You configure accounts, ownership, billing, protected environments, and secrets.
Codex then updates workflows if required, creates the release candidate, runs the
publishing workflows, verifies artifacts anonymously, fixes failures, deploys the
download manifest, completes the evidence, and archives finished prompts.

There are two credential classes:

| Class | Storage location | Examples |
| --- | --- | --- |
| Release credentials | GitHub protected environment secrets or the signing provider | Docker, Apple, Windows signing |
| Keprix runtime credentials | Keprix encrypted credential GUI | LLM, email, Telegram, CRM, sidecar keys |

Do not put release credentials in Keprix runtime settings or `.env` files.

## 2. Prepare the accounts

Confirm that you can sign in with multi-factor authentication to:

1. GitHub account that owns or administers `malike2356/keprix`.
2. PyPI and TestPyPI accounts with verified email addresses.
3. Docker Hub account or organization that owns the intended image namespace.
4. Apple Developer Program account with authority to create Developer ID
   certificates.
5. The chosen Windows code-signing provider.

Store recovery information in your password manager before continuing.

## 3. Configure GitHub environments

Open:
`https://github.com/malike2356/keprix/settings/environments`

Create these environments with the exact case-sensitive names:

- `testpypi`
- `pypi`
- `dockerhub`
- `desktop-macos`
- `desktop-windows`
- `desktop-linux`

For every environment:

1. Select **New environment**.
2. Enter the exact name above.
3. Select **Configure environment**.
4. Add yourself as a required reviewer where GitHub permits it.
5. Enable **Prevent self-review** only if another trusted reviewer is available.
6. Restrict deployment branches and tags to protected release tags when the UI
   supports tag patterns. Use `v*` for release tags.
7. Do not add broad repository secrets when an environment secret is sufficient.

`desktop-linux` requires approval but no signing secret. It prevents Linux release
packages from being published accidentally.

GitHub reference:
`https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments`

## 4. Protect the main branch and release tags

Open:
`https://github.com/malike2356/keprix/settings/rules`

### Main branch ruleset

1. Select **New ruleset**, then **New branch ruleset**.
2. Name it `protect-main` and set enforcement to **Active**.
3. Target the default branch, `main`.
4. Require pull requests before merging.
5. Require status checks. Select the Keprix CI, type-check, test, build, security,
   and release-readiness checks after each has appeared in Actions at least once.
6. Require branches to be up to date before merging.
7. Block force pushes and branch deletion.
8. Require conversation resolution.
9. Keep bypass access limited to the owner for emergency recovery. Prefer bypass
   through a pull request so an audit trail remains.

### Release tag ruleset

1. Select **New ruleset**, then **New tag ruleset**.
2. Name it `protect-release-tags` and set enforcement to **Active**.
3. Target tags matching `v*`.
4. Restrict tag creation, update, and deletion to the owner or release manager.
5. Do not permit force movement of published release tags.

GitHub reference:
`https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository`

## 5. Configure PyPI trusted publishing

Keprix uses OpenID Connect trusted publishing. Do not create or store a long-lived
PyPI API token.

### 5.1 TestPyPI

1. Sign in at `https://test.pypi.org/`.
2. Open your account publishing settings.
3. Add a pending GitHub publisher for project name `keprix` if the project does
   not exist. If it exists and you own it, open the project, select **Manage**, then
   **Publishing**, and add a publisher.
4. Enter:

| Field | Value |
| --- | --- |
| PyPI project name | `keprix` |
| GitHub owner | `malike2356` |
| GitHub repository | `keprix` |
| Workflow filename | `publish-pypi.yml` |
| Environment name | `testpypi` |

5. Save the publisher.

### 5.2 Production PyPI

1. Sign in at `https://pypi.org/`.
2. Repeat the publisher setup using:

| Field | Value |
| --- | --- |
| PyPI project name | `keprix` |
| GitHub owner | `malike2356` |
| GitHub repository | `keprix` |
| Workflow filename | `publish-pypi.yml` |
| Environment name | `pypi` |

3. Save the publisher.
4. Do not manually upload a package unless Codex reports that trusted publisher
   creation is impossible and provides a reviewed recovery plan.

Pending publishers do not reserve a package name until the first successful
publication. Tell Codex immediately after both publishers are configured so the
TestPyPI release can be performed promptly.

PyPI references:

- `https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/`
- `https://docs.pypi.org/trusted-publishers/adding-a-publisher/`

## 6. Configure Docker Hub publishing

The current workflows publish these public repositories:

- `carinaai/keprix-backend`
- `carinaai/keprix-frontend`

If `carinaai` is not the correct namespace, stop and tell Codex the approved
namespace before adding secrets. Codex must change and test every image reference
before release.

### 6.1 Create repositories

1. Sign in to Docker Hub.
2. Confirm you can create or administer repositories in the chosen namespace.
3. Create `keprix-backend` and `keprix-frontend` as public repositories.
4. Add short descriptions and links to `https://github.com/malike2356/keprix`.
5. Do not enable automated mutable builds that compete with GitHub Actions.

### 6.2 Create a scoped token

1. Open Docker account settings.
2. Select **Personal access tokens**, then **Generate new token**.
3. Name it `keprix-github-release`.
4. Select **Read and Write**. Do not grant Delete unless a documented rollback
   process later requires it.
5. Choose the shortest practical expiry and record a rotation reminder.
6. Copy the token directly into GitHub. It cannot be retrieved later.

For organization automation, prefer a Docker organization access token when your
plan supports one, so publishing is not tied to a personal account.

### 6.3 Add GitHub secrets

Open the `dockerhub` environment and add:

| Secret | Value |
| --- | --- |
| `DOCKERHUB_USERNAME` | Docker publisher username or service account name |
| `DOCKERHUB_TOKEN` | Scoped Docker access token |

Docker reference:
`https://docs.docker.com/security/access-tokens/`

## 7. Configure Apple signing and notarization

You need an active Apple Developer Program membership. Apple requires Developer ID
signing for software distributed outside the Mac App Store, followed by
notarization.

### 7.1 Record the account identifiers

1. Sign in at `https://developer.apple.com/account/`.
2. Record the Apple ID email used for notarization.
3. Record the 10-character Team ID from membership details.
4. Do not send either value in chat if you consider the account email sensitive.

### 7.2 Create and export a Developer ID Application certificate

Perform this on a trusted Mac:

1. Open **Keychain Access**.
2. Use **Certificate Assistant**, then **Request a Certificate From a Certificate
   Authority**.
3. Save the certificate signing request to disk.
4. In the Apple Developer portal, open **Certificates, Identifiers & Profiles**.
5. Create a **Developer ID Application** certificate using that request.
6. Download and install the certificate on the same Mac.
7. In Keychain Access, select the certificate and its private key, then export both
   as a password-protected `.p12` file.
8. Use a new strong export password and store the file plus password separately in
   your password manager.
9. Do not commit, email, or upload the `.p12` anywhere except the protected GitHub
   secret entry described below.

### 7.3 Create an app-specific password

1. Sign in at `https://account.apple.com/`.
2. Open **Sign-In and Security**, then **App-Specific Passwords**.
3. Create one named `Keprix GitHub notarization`.
4. Copy it directly to the GitHub environment secret.

### 7.4 Add GitHub secrets

Open the `desktop-macos` environment and add:

| Secret | Value |
| --- | --- |
| `APPLE_ID` | Apple ID email used for notarization |
| `APPLE_TEAM_ID` | Apple Developer Team ID |
| `APPLE_APP_SPECIFIC_PASSWORD` | App-specific password |
| `MAC_CSC_LINK` | Base64-encoded `.p12` certificate or secure supported certificate URL |
| `MAC_CSC_KEY_PASSWORD` | `.p12` export password |

Do not reuse Windows secret names for the Mac certificate. Codex will verify and,
if necessary, complete the workflow wiring before the first release run.

Apple references:

- `https://developer.apple.com/support/developer-id/`
- `https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution`
- `https://developer.apple.com/documentation/security/customizing-the-notarization-workflow`

## 8. Configure Windows code signing

Choose a code-signing provider that supports automated GitHub Actions signing.
Modern providers may use a hardware-backed cloud key instead of an exportable
certificate. Do not buy a certificate until the provider confirms unattended CI
support for Electron executables and installers.

### Option A: exportable certificate supported by the provider

Open the `desktop-windows` environment and add:

| Secret | Value |
| --- | --- |
| `WIN_CSC_LINK` | Base64 certificate payload or secure provider-supported URL |
| `WIN_CSC_KEY_PASSWORD` | Certificate password |

### Option B: cloud or hardware-backed signing

Do not invent values for `WIN_CSC_LINK`. Send Codex only:

- Provider name.
- Link to the provider's GitHub Actions integration documentation.
- Names of the required GitHub secrets, without their values.
- Whether the account and certificate are active.

Codex will adapt the workflow to the provider and tell you which protected secret
names to create.

## 9. Approve product and support policy

Reply to Codex with your decisions for the following non-secret items:

1. Supported bare-metal platforms: Linux, macOS, and WSL2 are currently proposed.
2. Supported desktop platforms: macOS arm64 and x64, Windows x64, Linux x64, and
   Linux arm64 are currently proposed, subject to clean-machine proof.
3. Community support channel: GitHub Discussions is proposed.
4. Security contact: confirm the address currently documented in `SECURITY.md`.
5. Telemetry: opt-in diagnostics only is proposed for self-hosted installs.
6. Release channel: begin with a beta or release candidate, not stable.
7. Docker namespace: confirm `carinaai` or provide the approved replacement.
8. First public version: confirm whether `v0.16.0` remains acceptable. Published
   package versions cannot be replaced, so Codex may recommend the next version.

## 10. Owner self-check

Before handoff, verify these items without exposing values:

- [ ] GitHub environments exist with exact names.
- [ ] Required reviewers and tag restrictions are enabled.
- [ ] `main` and `v*` rulesets are active.
- [ ] TestPyPI trusted publisher is registered.
- [ ] PyPI trusted publisher is registered.
- [ ] Both Docker repositories exist and are public.
- [ ] `DOCKERHUB_USERNAME` exists in `dockerhub`.
- [ ] `DOCKERHUB_TOKEN` exists in `dockerhub`.
- [ ] Apple Developer membership is active.
- [ ] All five Apple secrets exist in `desktop-macos`.
- [ ] Windows provider is selected and its required secrets exist.
- [ ] Product and support decisions are recorded.
- [ ] No secret was pasted into chat or committed.

GitHub displays secret names after creation but does not reveal their stored
values. A visible secret name is sufficient evidence for the handoff.

## 11. Send this non-secret handoff to Codex

Copy the following block, fill it in, and send it without secret values:

```text
Keprix release configuration handoff

GitHub admin access: confirmed / not confirmed
Repository public: yes / no
Environments created: testpypi, pypi, dockerhub, desktop-macos, desktop-windows, desktop-linux
Required reviewers enabled: yes / no
Main ruleset active: yes / no
Release tag ruleset active: yes / no

TestPyPI trusted publisher: configured / blocked
PyPI trusted publisher: configured / blocked

Docker namespace: carinaai / replacement namespace
Docker repositories public: yes / no
Docker environment secret names present: yes / no

Apple Developer membership active: yes / no
Apple environment secret names present: yes / no

Windows signing provider: provider name
Windows signing method: exportable certificate / cloud signing
Windows environment secret names present: yes / no
Provider documentation URL: URL only, no credentials

Approved first channel: beta / release candidate
Approved first version: version or ask Codex to select
Security contact confirmed: yes / replacement address
Support channel approved: GitHub Discussions / replacement
Opt-in self-hosted diagnostics approved: yes / no

I authorize Codex to update the release workflows, create the release candidate,
run protected publishing jobs, deploy the verified manifest, and complete release
evidence. I will manually approve protected GitHub environment jobs when prompted.
```

## 12. What Codex will do after handoff

1. Inspect only the presence and names of required configuration, never secret
   values.
2. Correct Mac or Windows provider workflow wiring.
3. Confirm the version is unused across GitHub, PyPI, TestPyPI, and Docker.
4. Run the complete private quality gate and clean-build matrix.
5. Create a protected immutable release-candidate tag.
6. Publish to TestPyPI and verify anonymous installation.
7. Build and verify multi-architecture Docker images.
8. Build signed desktop packages, verify signatures, notarization, installation,
   updates, rollback, and uninstall.
9. Publish the GitHub prerelease and immutable release manifest.
10. Deploy the manifest-driven download centre locally and to Contabo.
11. Run anonymous downloads and clean-machine stranger tests.
12. Run `KEPRIX_GTM_REQUIRE_LIVE_ARTIFACTS=1 bash scripts/check-worldwide-gtm-gate.sh`.
13. Record residual risks and request final stable-launch approval.
14. Archive each completed prompt only after its external evidence passes.

The owner should expect GitHub approval prompts during publishing. Approval allows
the job to access the relevant environment secrets without revealing those secrets
to Codex or the workflow logs.
