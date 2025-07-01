# OpenAI Rate Limiting Guide

This project implements intelligent rate limiting to respect OpenAI's API limits and avoid rate limit errors.

## Usage Tiers

OpenAI organizes users into tiers based on their spending history:

| Tier | Qualification | Usage Limit | Typical RPM | Typical TPM |
|------|--------------|-------------|-------------|-------------|
| **Free** | New users | $100/month | 3 | 40,000 |
| **Tier 1** | $5+ spent | $100/month | 500 | 200,000 |
| **Tier 2** | $50+ spent, 7+ days | $500/month | 5,000 | 450,000 |
| **Tier 3** | $100+ spent, 7+ days | $1,000/month | 5,000 | 600,000 |
| **Tier 4** | $250+ spent, 14+ days | $5,000/month | 10,000 | 800,000 |
| **Tier 5** | $1,000+ spent, 30+ days | $200,000/month | 10,000 | 2,000,000 |

*RPM = Requests Per Minute, TPM = Tokens Per Minute*

## Configuration

### Method 1: Environment Variable
Set your tier in the `.env` file:
```bash
OPENAI_TIER=1  # Set to your actual tier (0-5)
```

### Method 2: Command Line
Override tier for a single run:
```bash
python cli.py VIDEO_ID --openai-tier 2
```

### Method 3: Conservative Mode (Default)
Leave `OPENAI_TIER` empty for automatic conservative rate limiting.

## How Rate Limiting Works

The tool automatically:

1. **Calculates delays** based on your tier's limits
2. **Tracks usage** across requests and tokens
3. **Waits proactively** to avoid hitting limits
4. **Uses exponential backoff** on rate limit errors
5. **Adds safety margins** (uses 80% of limits)

## Finding Your Tier

1. **Check spending**: Visit [OpenAI Platform → Billing](https://platform.openai.com/account/billing)
2. **View limits**: Check [Usage & Limits](https://platform.openai.com/settings/organization/limits)
3. **Start conservative**: Use Tier 0 or leave blank if unsure

## Examples

### Free Tier (Very Limited)
```bash
# Use minimal slides for testing
python cli.py VIDEO_ID --openai-tier 0 --max-slides 2 --dry-run
```

### Tier 1 ($5+ spent)
```bash
# Moderate usage
python cli.py VIDEO_ID --openai-tier 1 --max-slides 10
```

### Tier 2+ (Higher limits)
```bash
# Full processing
python cli.py VIDEO_ID --openai-tier 2
```

## Rate Limiting Behavior

### Free Tier (Tier 0)
- **3 requests/minute** → 20 second delays
- Very conservative processing
- Best for testing with `--dry-run`

### Tier 1
- **500 requests/minute** → ~0.1 second delays  
- Suitable for regular use
- Can process most videos

### Tier 2+
- **5000+ requests/minute** → Minimal delays
- Fast processing
- No practical limitations for this tool

## Troubleshooting

### Still Getting Rate Limit Errors?
1. **Verify your tier**: Check [OpenAI Platform](https://platform.openai.com/settings/organization/limits)
2. **Lower the tier setting**: Start with Tier 0
3. **Reduce slides**: Use `--max-slides 5`
4. **Use dry-run**: Test with `--dry-run` first

### Error: "Maximum number of retries exceeded"
- Your API key may have insufficient quota
- Check billing status and add credits
- Use a lower tier setting

### Very Slow Processing?
- You may be on Free tier (Tier 0)
- Upgrade your OpenAI account
- Consider using `--dry-run` for testing

## Best Practices

1. **Start conservative**: Use Tier 0 or leave tier unset
2. **Test with dry-run**: Use `--dry-run` for initial testing  
3. **Monitor usage**: Check OpenAI dashboard for actual usage
4. **Upgrade gradually**: Move to higher tiers as needed
5. **Use fewer slides**: Start with `--max-slides 5` for testing

## Technical Details

The rate limiter:
- Tracks requests and tokens per minute
- Waits proactively when approaching 80% of limits
- Uses exponential backoff on API errors
- Resets counters every minute
- Estimates token usage before requests

This ensures reliable operation within your tier's limits while maximizing processing speed.