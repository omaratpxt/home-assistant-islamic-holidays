# Islamic Holidays (Home Assistant)

Custom integration that adds a **read-only calendar** with **Islamic holidays and major holy days only**—separate from the built-in country “Holiday” calendars (Germany, Saudi Arabia, etc.), which mix civic and religious dates.

Data is loaded automatically from the **[Islamic Network AlAdhan API](https://aladhan.com/islamic-calendar-api)** (`api.aladhan.com`), specifically the Gregorian → Hijri calendar endpoint that annotates each day with holiday names.

## Accuracy and limitations

- The AlAdhan service may **rate-limit** heavy traffic; this integration **spaces** month requests and **retries** on HTTP 429 (honouring `Retry-After` when present).
- Dates are **computed** using the calendar logic returned by the API (e.g. `HJCoSA` in responses). They are **not** guaranteed to match every mosque or country that follows **local moonsighting**; official and community dates can differ by a day (for example, **Eid al-Adha** may appear on a different Gregorian day than in your country’s announcement—try **Hijri adjustment** if AlAdhan’s mapping is consistently shifted for you).
- Optional **Hijri adjustment** (-3…+3) is passed through to AlAdhan as the `adjustment` query parameter when supported by the API.
- **Major holidays** mode filters to a fixed allowlist of widely observed days (Eids, Ramadan start, Laylat al-Qadr, Ashura, Mawlid, etc.) and **excludes** tariqa-specific Urs/birth observances that AlAdhan also lists. Use **All holidays** to include every label the API returns for each day.
- **Eid-ul-Fitr** and **Eid-ul-Adha** are shown as **multi-day** all-day events (**3** and **4** Gregorian days) starting on the date AlAdhan returns, since the API usually marks only the first day.

## Requirements

- Home Assistant **2023.1** or newer

## Installation (HACS)

1. Open **HACS** → ⋮ **Custom repositories**
2. Add this repository URL and category **Integration**
3. Search for **Islamic Holidays**, download, and restart Home Assistant

### Manual install

Copy `custom_components/islamic_holidays/` into your configuration directory:

```text
config/
└── custom_components/
    └── islamic_holidays/
```

Restart Home Assistant.

## Maintainers (CI and HACS default inclusion)

The [HACS Action](https://github.com/hacs/action) and [default repository checks](https://hacs.xyz/docs/publish/include/) expect:

1. **Brand images** in `custom_components/islamic_holidays/brand/icon.png` (and optionally `logo.png`). These must be **committed** to the repo; HACS does not use only the CDN fallback unless your domain exists in [home-assistant/brands](https://github.com/home-assistant/brands).
2. **GitHub repository topics** (Settings → General → Topics). They cannot be set from files inside the repo. Add at least a few meaningful topics, for example: `home-assistant`, `hacs-integration`, `integration`, `islamic-calendar`, `calendar`.

For inclusion in the default HACS store you also need **Hassfest** in GitHub Actions and a **GitHub Release**; see the [HACS publish docs](https://hacs.xyz/docs/publish/include/).

## Configuration

1. **Settings** → **Devices & services** → **Add integration**
2. Search for **Islamic Holidays**
3. Set **Calendar name**, **Holiday filter** (major vs all), and optional **Hijri adjustment**
4. After setup, use **Configure** to change **refresh interval** (6–168 hours)

The calendar covers **24 consecutive Gregorian months**, starting **12 months before** the current month (so past months like May stay available mid-year) and refreshes on the configured interval.

## Usage

- Entity appears as a standard **calendar** (e.g. `calendar.islamic_holidays`) for dashboards and **`calendar` triggers** in automations.
- The integration is **read-only**; you cannot create or edit events in Home Assistant.

## Credits

- Calendar data: [AlAdhan / Islamic Network](https://aladhan.com/)
- Layout inspired by [home-assistant-nayax](https://github.com/alpenava/home-assistant-nayax)
- Integration **icon** and **logo** in `custom_components/islamic_holidays/brand/` are based on the official Home Assistant [Brands](https://github.com/home-assistant/brands) assets for the core **Islamic Prayer Times** integration (`integration/islamic_prayer_times`), from the CDN: [icon](https://brands.home-assistant.io/_/integration/islamic_prayer_times/icon.png), [logo](https://brands.home-assistant.io/_/integration/islamic_prayer_times/logo.png). No separate entry was added under `brands/` for this custom integration.

## License

MIT — see [LICENSE](LICENSE).
