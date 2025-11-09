# CrowdFunding with ERC20

# Getting Started

## Prerequisites

- [git](https://git-scm.com/)
  - You'll know you've done it right if you can run `git --version` and see a version number.
- [anvil](https://book.getfoundry.sh/anvil/)
  - You'll know you've done it right if you can run `anvil --version` and see an output like `anvil 0.2.0 (fdd321b 2024-10-15T00:21:13.119600000Z)`
- [moccasin](https://github.com/Cyfrin/moccasin)
  - You'll know you've done it right if you can run `mox --version` and get an output like: `Moccasin CLI v0.3.0`

## Installation

```bash
git clone https://github.com/ladieweb3/crowdfunding-with-erc20
cd crowdfunding-with-erc20
```

## Quickstart

```bash
mox run deploy 
```

# Usage

## Compile

```bash
mox compile
```

## Test

(These will fail intentionally!)

```bash
mox test
```

# Formatting

## Python

```
uv run ruff check --select I --fix
uv run ruff check . --fix
```

## Vyper 

```
uv run mamushi contracts/
```