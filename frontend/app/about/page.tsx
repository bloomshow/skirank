import Link from "next/link";

export const metadata = { title: "How It Works — SkiRank" };

const SCORE_BANDS = [
  {
    range: "85–100",
    label: "Exceptional",
    dot: "bg-green-500",
    badge: "bg-green-100 text-green-800",
    desc: "Rare, world-class conditions. Deep base, recent fresh snow, perfect temperatures. Drop everything and go.",
  },
  {
    range: "70–84",
    label: "Very Good",
    dot: "bg-green-400",
    badge: "bg-green-50 text-green-700 border border-green-200",
    desc: "Excellent conditions by any measure. Great base, good snow quality, comfortable temps.",
  },
  {
    range: "55–69",
    label: "Good",
    dot: "bg-yellow-400",
    badge: "bg-yellow-100 text-yellow-800",
    desc: "Solid skiing. Most runs open, decent snow quality. Worth the trip.",
  },
  {
    range: "40–54",
    label: "Average",
    dot: "bg-yellow-500",
    badge: "bg-amber-100 text-amber-800",
    desc: "Skiable but unremarkable. Thin base or icy patches possible. Fine for a local day trip.",
  },
  {
    range: "25–39",
    label: "Below Average",
    dot: "bg-orange-500",
    badge: "bg-orange-100 text-orange-800",
    desc: "Marginal conditions. Limited open terrain or weather issues.",
  },
  {
    range: "0–24",
    label: "Poor",
    dot: "bg-red-500",
    badge: "bg-red-100 text-red-800",
    desc: "Not recommended. Very thin base, warm temps, or high winds likely causing closures.",
  },
];

const COMPONENTS = [
  {
    icon: "❄️",
    name: "Base Depth",
    weight: "25%",
    desc: "How deep is the existing snowpack compared to the historical average for that resort at this time of year? A resort sitting at 200% of its seasonal average scores very highly here. This tells you how much of a cushion exists even if it doesn't snow again.",
  },
  {
    icon: "🌨️",
    name: "Fresh Snow",
    weight: "35%",
    desc: "The biggest factor. Combines actual snowfall from the last 72 hours with forecasted snowfall over your selected trip window. Powder hunters should pay most attention to this number. A resort that just received 60cm with more forecast will dominate the rankings.",
  },
  {
    icon: "🌡️",
    name: "Temperature",
    weight: "20%",
    desc: "Cold, stable temperatures preserve snow quality and keep conditions consistent. The ideal range is around −5°C to −15°C. Scores drop sharply as temperatures approach 0°C (melting and icy refreezes) and at extreme cold below −25°C.",
  },
  {
    icon: "💨",
    name: "Wind",
    weight: "10%",
    desc: "High winds close lifts, create dangerous conditions, and scour snow off exposed terrain. A calm, light-wind day scores 100 here. Anything above 60 km/h scores very poorly.",
  },
  {
    icon: "📡",
    name: "Forecast Confidence",
    weight: "10%",
    desc: "How reliable is the underlying data? A score based on today's actual observed conditions is more trustworthy than one based on a 14-day forecast. This component automatically discounts scores the further out the forecast window extends, so you always know how much certainty to attach to a ranking.",
  },
];

const HORIZONS = [
  {
    window: "Today",
    source: "~100% observed data",
    use: "Highly reliable. Use when deciding where to ski this weekend.",
    reliability: 100,
  },
  {
    window: "3 Days",
    source: "~60% observed, 40% forecast",
    use: "Still quite reliable. Good for short-notice planning.",
    reliability: 75,
  },
  {
    window: "7 Days",
    source: "~30% observed, 70% forecast",
    use: "Good directional signal. Treat with some caution.",
    reliability: 45,
  },
  {
    window: "14 Days",
    source: "~10% observed, 90% forecast",
    use: "Use for planning direction only — not a guarantee.",
    reliability: 20,
  },
];

const DATA_SOURCES = [
  {
    name: "Open-Meteo",
    desc: "Primary weather and forecast data. Free, open-source, European weather model. Provides current conditions and 16-day forecasts for every resort location.",
  },
  {
    name: "USDA Snotel Network",
    desc: "Automated snowpack sensors across North American mountain ranges. Provides ground-truth snow depth readings for resorts in the US and Canada.",
  },
  {
    name: "NOAA / National Weather Service",
    desc: "Supplementary data for North American resorts, particularly for extended seasonal outlooks.",
  },
  {
    name: "Resort Metadata",
    desc: "Elevation, aspect, latitude, and terrain data compiled from OpenStreetMap, resort websites, and public databases. Used to apply terrain-specific adjustments to scores.",
  },
];

const LIMITATIONS = [
  {
    title: "Crowding",
    desc: "A resort can score 95 and be packed with spring break skiers. We don't have lift queue data.",
  },
  {
    title: "Price & accessibility",
    desc: "A remote resort in Japan might outscore one 2 hours from your door. Distance and cost are not factored in.",
  },
  {
    title: "Grooming quality",
    desc: "We don't have real-time grooming reports. Base depth and temperature are proxies for surface quality but not perfect ones.",
  },
  {
    title: "Terrain variety",
    desc: "A resort with one amazing run and a score of 80 is very different from a large resort with the same score across 200 runs.",
  },
  {
    title: "Forecast uncertainty",
    desc: "Beyond 7 days, treat scores as directional guidance only.",
  },
];

export default function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-16 space-y-20">

      {/* ── Hero ── */}
      <section className="space-y-5">
        <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight">
          How SkiRank Works
        </h1>
        <p className="text-lg text-slate-500 font-medium">
          Independent, data-driven snow condition rankings — updated every morning at 6am UTC.
        </p>
        <p className="text-slate-600 leading-relaxed">
          SkiRank ranks every major ski resort in the world based on objective weather and snowpack
          data — not self-reported resort numbers. We combine current conditions with multi-day
          forecasts to help you find the best snow, whether you&apos;re heading out this weekend or
          planning a trip weeks from now.
        </p>
      </section>

      {/* ── Score bands ── */}
      <section className="space-y-6">
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-slate-800">What Does 0–100 Mean?</h2>
          <p className="text-slate-600 leading-relaxed">
            Every resort receives a single composite score from 0 to 100. Think of it like a
            restaurant review — one number that distills everything that matters into an instant read.
          </p>
        </div>

        <div className="space-y-2">
          {SCORE_BANDS.map(({ range, label, dot, badge, desc }) => (
            <div
              key={range}
              className="flex items-start gap-4 bg-white border border-slate-200 rounded-xl p-4"
            >
              <div className="flex items-center gap-2 w-32 shrink-0 pt-0.5">
                <span className={`inline-block w-2.5 h-2.5 rounded-full shrink-0 ${dot}`} />
                <span className="text-sm font-bold text-slate-800">{range}</span>
              </div>
              <div className="flex-1 min-w-0">
                <span className={`inline-block text-xs font-semibold px-2.5 py-0.5 rounded-full mb-1.5 ${badge}`}>
                  {label}
                </span>
                <p className="text-sm text-slate-600 leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Score components ── */}
      <section className="space-y-6">
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-slate-800">What Goes Into the Score</h2>
          <p className="text-slate-600 leading-relaxed">
            The composite score is made up of five components. Each is scored 0–100 and combined
            using weighted averages. You can adjust the weights yourself using the sliders on the
            rankings page.
          </p>
        </div>

        <div className="space-y-3">
          {COMPONENTS.map(({ icon, name, weight, desc }) => (
            <div key={name} className="bg-white border border-slate-200 rounded-xl p-5 flex gap-4">
              <div className="text-2xl shrink-0 mt-0.5">{icon}</div>
              <div className="flex-1 space-y-1.5">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="font-semibold text-slate-800">{name}</h3>
                  <span className="text-xs bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full font-medium">
                    {weight} default
                  </span>
                </div>
                <p className="text-sm text-slate-600 leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Trip windows ── */}
      <section className="space-y-6">
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-slate-800">Today vs. Future — The Trip Window</h2>
          <p className="text-slate-600 leading-relaxed">
            Changing the horizon from <strong>Today</strong> to <strong>7 Days</strong> or{" "}
            <strong>14 Days</strong> shifts the score from being based on current conditions to
            being based on weather forecasts. Here&apos;s how to think about each:
          </p>
        </div>

        <div className="space-y-2">
          {HORIZONS.map(({ window, source, use, reliability }) => (
            <div
              key={window}
              className="bg-white border border-slate-200 rounded-xl p-4 flex items-start gap-4"
            >
              <div className="w-20 shrink-0">
                <p className="font-bold text-slate-800 text-sm">{window}</p>
                {/* Reliability bar */}
                <div className="mt-1.5 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full"
                    style={{ width: `${reliability}%` }}
                  />
                </div>
              </div>
              <div className="flex-1 space-y-1">
                <p className="text-xs text-slate-500 font-medium">{source}</p>
                <p className="text-sm text-slate-600">{use}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
          <p className="text-sm text-slate-600 leading-relaxed">
            <span className="font-semibold text-slate-800">Note:</span> The 14-day score is saying
            &ldquo;based on current weather models, this is where conditions are trending&rdquo; —
            not a promise. Think of it the way you&apos;d treat a two-week weather forecast: useful
            signal, not gospel.
          </p>
        </div>
      </section>

      {/* ── Sliders / customisation ── */}
      <section className="space-y-5">
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-slate-800">Customising the Score</h2>
          <p className="text-slate-600 leading-relaxed">
            Not everyone skis the same way. The weight sliders on the rankings page let you
            personalise what matters:
          </p>
        </div>

        <div className="grid sm:grid-cols-2 gap-3">
          {[
            {
              label: "Powder hunter?",
              tip: "Increase Fresh Snow to 60–70%, reduce Base Depth",
              icon: "🌨️",
            },
            {
              label: "Groomer day?",
              tip: "Increase Base Depth and Temperature, lower Fresh Snow",
              icon: "🎿",
            },
            {
              label: "Skiing with kids?",
              tip: "Increase Wind and Temperature — comfort matters more than powder",
              icon: "👨‍👧",
            },
            {
              label: "Late-season spring skiing?",
              tip: "Temperature becomes critical — increase its weight heavily",
              icon: "☀️",
            },
          ].map(({ label, tip, icon }) => (
            <div
              key={label}
              className="bg-white border border-slate-200 rounded-xl p-4 flex gap-3 items-start"
            >
              <span className="text-xl shrink-0">{icon}</span>
              <div>
                <p className="text-sm font-semibold text-slate-800">{label}</p>
                <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{tip}</p>
              </div>
            </div>
          ))}
        </div>

        <p className="text-sm text-slate-500">
          Your slider settings are saved automatically so the rankings always reflect your preferences.
        </p>
      </section>

      {/* ── Data sources ── */}
      <section className="space-y-5">
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-slate-800">Data Sources</h2>
          <p className="text-slate-600 leading-relaxed">
            We use independent, third-party data sources — never resort self-reported figures.
            Resorts have an obvious incentive to paint conditions in the best possible light.
            We don&apos;t.
          </p>
        </div>

        <div className="space-y-2">
          {DATA_SOURCES.map(({ name, desc }) => (
            <div key={name} className="bg-white border border-slate-200 rounded-xl p-4 flex gap-4">
              <div className="w-1 rounded-full bg-blue-400 shrink-0 self-stretch" />
              <div>
                <p className="font-semibold text-slate-800 text-sm">{name}</p>
                <p className="text-sm text-slate-600 mt-0.5 leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>

        <p className="text-sm text-slate-500 font-medium">
          Data is refreshed daily at 06:00 UTC.
        </p>
      </section>

      {/* ── Limitations ── */}
      <section className="space-y-5">
        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-slate-800">What the Score Doesn&apos;t Tell You</h2>
          <p className="text-slate-600 leading-relaxed">
            We believe in being honest about our limitations.
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100">
          {LIMITATIONS.map(({ title, desc }) => (
            <div key={title} className="px-5 py-4 flex gap-3">
              <span className="text-slate-300 font-bold text-lg leading-none mt-0.5 shrink-0">—</span>
              <div>
                <span className="font-semibold text-slate-800 text-sm">{title} </span>
                <span className="text-sm text-slate-600 leading-relaxed">{desc}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Footer CTA ── */}
      <section className="bg-blue-600 rounded-2xl p-10 text-center space-y-4">
        <h2 className="text-2xl font-bold text-white">Ready to find your next powder day?</h2>
        <Link
          href="/rankings"
          className="inline-block px-8 py-3 bg-white text-blue-700 font-semibold rounded-xl hover:bg-blue-50 transition-colors shadow-md"
        >
          View Rankings →
        </Link>
      </section>

    </div>
  );
}
