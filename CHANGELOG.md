# Changelog

## [1.6.0](https://github.com/yohi/turnshade/compare/v1.5.0...v1.6.0) (2026-10-18)


### Features

* add fail-closed POSIX installer for Chrome Linux external updates ([5f18f91](https://github.com/yohi/turnshade/commit/5f18f91dae4c8552fcc79c10aba79d09bc4dd3ea))
* curl | sh installer supporting Chrome Stable, Beta and Dev ([a3b8ea4](https://github.com/yohi/turnshade/commit/a3b8ea461e29f8649bee4e545d2d1135dbade8b3))
* include pinned-ID install.sh in atomic Pages deploy and reuse signed CRX ([69cc581](https://github.com/yohi/turnshade/commit/69cc5814e105053506b6129d2f3776c7eef55df5))
* select Chrome Stable Beta or Dev and isolate system registration per channel ([2d571f0](https://github.com/yohi/turnshade/commit/2d571f0fff6512c78758064066c2d538f3f946f5))


### Bug Fixes

* defer curl-piped installer execution until complete main definition and validate channel binary ([201c932](https://github.com/yohi/turnshade/commit/201c932ee95e3110fa920fcd8f94ce0928688408))
* fail closed on failed update-manifest download ([5ed5cf6](https://github.com/yohi/turnshade/commit/5ed5cf66176238ff2e45a7f421c01259ca206be0))
* respect both official Chrome Linux extension directories and avoid duplicate registrations ([f275ce7](https://github.com/yohi/turnshade/commit/f275ce7b5ccbba97d80bbf953adca0f1cd8cf491))
* verify structured CRX3 proof identity with and without signing key ([817aaab](https://github.com/yohi/turnshade/commit/817aaab262db9b4a3ee462344b4fabd0c21b552c))

## [1.5.0](https://github.com/yohi/turnshade/compare/v1.4.0...v1.5.0) (2026-10-18)


### Features

* add manual secret-backed CRX3 signing for published releases ([cbeda46](https://github.com/yohi/turnshade/commit/cbeda46f2b0d1b6bcba827dad84bc58a5c0a9f6e))
* build pinned-ID Chrome update XML and atomic Pages CRX site ([5584805](https://github.com/yohi/turnshade/commit/5584805daef37c83b59df36c107a74b72638797b))
* package verified release ZIP as signed CRX3 using Chrome ([de41e04](https://github.com/yohi/turnshade/commit/de41e04b308cb5cf950f19b02de1b52b1a0a7e1c))
* reusable signed release to atomic Pages update deployment ([a0a8691](https://github.com/yohi/turnshade/commit/a0a869196ea905253c7b7184884155b987edea00))
* self-host signed CRX3 via GitHub Releases + Pages auto-update ([5146308](https://github.com/yohi/turnshade/commit/5146308bcd5936d52474a3941c34a947bd1b7ce9))
* set Chrome self-hosted update URL to GitHub Pages ([de408f3](https://github.com/yohi/turnshade/commit/de408f3fd8072441e501d540ce33bf8565153757))
* validate and allowlist release ZIP before CRX signing ([27b6c80](https://github.com/yohi/turnshade/commit/27b6c808654c48f6bbcc8bb73b0c2c865e683a91))


### Bug Fixes

* correct CRX3 size diagnostic ([7ddde22](https://github.com/yohi/turnshade/commit/7ddde22209b283f9f35d8d02774ba8c479c3c4eb))
* disallow signing releases without self-hosted update URL ([11bd76e](https://github.com/yohi/turnshade/commit/11bd76ea5a24bad4ff433f5b040da9c15d796ad0))

## [1.4.0](https://github.com/yohi/turnshade/compare/v1.3.0...v1.4.0) (2026-10-18)


### Features

* derive next-turn arrow from split tab ordering with manual reverse ([44dfea5](https://github.com/yohi/turnshade/commit/44dfea5efafe07f5b4adef623d1519bdd7ab1878))
* describe directional border in manifest ([47acd8b](https://github.com/yohi/turnshade/commit/47acd8b62a0bdb2737792fd05490002ff9bc0b83))
* expose red border mode and arrow direction override in popup ([321f581](https://github.com/yohi/turnshade/commit/321f581f5e89cec6f8b48377a17aa68bf7f74268))
* expose red border mode and arrow direction override in popup ([db4f042](https://github.com/yohi/turnshade/commit/db4f042d93a47626a11dfd877e8a4543612613b5))
* mark last sent chat with red border and next-turn arrows ([cca52a9](https://github.com/yohi/turnshade/commit/cca52a9d3563b5452de098984acd0c0a0dcd8244))
* replace dimming overlay with red border and directional cue ([4235eda](https://github.com/yohi/turnshade/commit/4235edae20dfc79d68af745d342233c0111347cb))

## [1.3.0](https://github.com/yohi/turnshade/compare/v1.2.0...v1.3.0) (2026-10-15)


### Features

* allow Gemini host and page injection ([ad4be6f](https://github.com/yohi/turnshade/commit/ad4be6fc0ad5c62385a3cba417ba2395022dd4e8))
* detect Gemini user turns and send events ([ae152cb](https://github.com/yohi/turnshade/commit/ae152cb67559aa5b7c809fe28b340e1787d8d05a))
* recognize ChatGPT and Gemini pair URLs ([e092bdb](https://github.com/yohi/turnshade/commit/e092bdb0bb4773df18bfd1dcedf50701d8afe950))
* show provider pairing diagnostics ([6431add](https://github.com/yohi/turnshade/commit/6431add5806c8a8174b7eee5ccf1ad2b0fc19c8b))
* support ChatGPT × Gemini and Gemini × Gemini split turns ([4df7920](https://github.com/yohi/turnshade/commit/4df7920f75f1b053861473e4f5fcbc4a6622f860))

## [1.2.0](https://github.com/yohi/turnshade/compare/v1.1.0...v1.2.0) (2026-10-15)


### Features

* allow Gemini host and page injection ([ad4be6f](https://github.com/yohi/turnshade/commit/ad4be6fc0ad5c62385a3cba417ba2395022dd4e8))
* detect Gemini user turns and send events ([ae152cb](https://github.com/yohi/turnshade/commit/ae152cb67559aa5b7c809fe28b340e1787d8d05a))
* recognize ChatGPT and Gemini pair URLs ([e092bdb](https://github.com/yohi/turnshade/commit/e092bdb0bb4773df18bfd1dcedf50701d8afe950))
* show provider pairing diagnostics ([6431add](https://github.com/yohi/turnshade/commit/6431add5806c8a8174b7eee5ccf1ad2b0fc19c8b))
* support ChatGPT × Gemini and Gemini × Gemini split turns ([4df7920](https://github.com/yohi/turnshade/commit/4df7920f75f1b053861473e4f5fcbc4a6622f860))
