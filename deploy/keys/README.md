# Release signing public key
#
# Operators publish an ASCII-armored public key here as `keprix-release.gpg.asc`.
# Until a production key is published, `scripts/verify-release.sh` can use:
#
#   KEPRIX_RELEASE_PUBKEY=/path/to/key.asc
#   # or for local testing only:
#   KEPRIX_REQUIRE_RELEASE_SIG=0 bash scripts/verify-release.sh --allow-unsigned ...
#
# Create and export a signing key (maintainers):
#
#   gpg --full-generate-key
#   gpg --armor --export KEY_ID > deploy/keys/keprix-release.gpg.asc
#   bash scripts/build-release-artifact.sh --version vX.Y.Z
#   GPG_KEY_ID=KEY_ID bash scripts/sign-release.sh
#
# Never commit the private key.
