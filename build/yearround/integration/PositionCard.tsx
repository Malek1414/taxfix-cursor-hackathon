/**
 * PositionCard — the one card that goes on the Taxfix home screen, above the
 * "Steuerjahr 2025" category rows. Uses the app's existing idiom: a refund pill,
 * category-style rows (icon tile · label · euro chip · chevron) and the sticky
 * "Als nächstes" footer target. No new navigation: onOpenMove routes into the
 * existing Ausgaben question for that item, pre-filled for the current year.
 *
 * Data: GET /v1/demo/card (or POST /v1/card with the user's profile).
 * Money arrives as strings; the client never does arithmetic.
 */
import React, { useEffect, useState } from "react";
import { View, Text, Pressable, StyleSheet, ActivityIndicator } from "react-native";

type Move = {
  label: string; status: "worth" | "zero" | "escalate"; saving_eur: string;
  citation: string; citation_resolves: boolean; why: string; kind: string; shown: boolean;
};
type Card = {
  asOf: string; headline: { amountEur: string; label: string };
  deadline: { date: string; daysLeft: number; basis: string };
  afterPlan: { amountEur: string; deltaEur: string }; moves: Move[]; disclosure: string;
};

const ICON: Record<string, string> = { handwerker: "🔌", haushalt: "🧹", werbungskosten: "💻", homeoffice: "🏠", spende: "💚", other: "👥" };
const eur = (s: string) => `${Number(s).toLocaleString("de-DE", { minimumFractionDigits: 0, maximumFractionDigits: 0 })} €`;

export function PositionCard({ baseUrl = "http://127.0.0.1:8787", onOpenMove }:
  { baseUrl?: string; onOpenMove?: (m: Move) => void }) {
  const [card, setCard] = useState<Card | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${baseUrl}/v1/demo/card`).then(r => r.json()).then(setCard).catch(e => setErr(String(e)));
  }, [baseUrl]);

  if (err) return <View style={s.card}><Text style={s.muted}>Position nicht verfügbar — {err}</Text></View>;
  if (!card) return <View style={s.card}><ActivityIndicator /></View>;

  const worth = card.moves.filter(m => m.status === "worth");
  const refused = card.moves.filter(m => m.status !== "worth");

  return (
    <View style={s.card}>
      <Text style={s.eyebrow}>Steuerjahr {card.asOf.slice(0, 4)} · Stand heute</Text>
      <View style={s.headRow}>
        <Text style={s.headLabel}>Wenn du heute abgibst</Text>
        <View style={s.pill}><Text style={s.pillText}>{eur(card.headline.amountEur)}</Text></View>
      </View>
      <Text style={s.muted}>{card.deadline.daysLeft} Tage bis 31.12. — {card.deadline.basis}, nicht wir.</Text>

      {worth.map(m => (
        <Pressable key={m.label} style={s.row} onPress={() => onOpenMove?.(m)} accessibilityRole="button">
          <View style={s.tile}><Text style={s.tileText}>{ICON[m.kind] ?? "•"}</Text></View>
          <View style={{ flex: 1 }}>
            <Text style={s.rowLabel}>{m.label}</Text>
            <Text style={s.rowWhy} numberOfLines={2}>{m.why}</Text>
          </View>
          <Text style={s.chip}>+{eur(m.saving_eur)}</Text>
          <Text style={s.chev}>›</Text>
        </Pressable>
      ))}

      <View style={s.after}>
        <Text style={s.afterLabel}>Nach diesen {worth.length} Zügen</Text>
        <Text style={s.afterValue}>{eur(card.afterPlan.amountEur)}</Text>
      </View>

      {refused.map(m => (
        <Pressable key={m.label} style={[s.row, s.rowWarn]} onPress={() => onOpenMove?.(m)}>
          <View style={[s.tile, s.tileWarn]}><Text style={s.tileText}>{m.status === "zero" ? "0 €" : "?"}</Text></View>
          <View style={{ flex: 1 }}>
            <Text style={s.rowLabel}>{m.status === "zero" ? "Lohnt sich nicht: " : "Frag einen Experten: "}{m.label}</Text>
            <Text style={s.rowWhy} numberOfLines={3}>{m.why}</Text>
          </View>
        </Pressable>
      ))}
      <Text style={s.disclosure}>{card.disclosure}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  card: { backgroundColor: "#fff", borderRadius: 20, padding: 16, marginHorizontal: 16, marginBottom: 12, gap: 10 },
  eyebrow: { fontSize: 11, letterSpacing: 0.8, color: "#5b6b5e", textTransform: "uppercase", fontWeight: "600" },
  headRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  headLabel: { fontSize: 20, fontWeight: "700", color: "#0d2b15" },
  pill: { backgroundColor: "#dff5c2", borderRadius: 999, paddingHorizontal: 14, paddingVertical: 8 },
  pillText: { fontSize: 18, fontWeight: "700", color: "#0f5c2e", fontVariant: ["tabular-nums"] },
  muted: { fontSize: 13, color: "#5b6b5e" },
  row: { flexDirection: "row", alignItems: "center", gap: 12, backgroundColor: "#f6f7f2", borderRadius: 14, padding: 12 },
  rowWarn: { backgroundColor: "#fff4dd" },
  tile: { width: 44, height: 44, borderRadius: 12, backgroundColor: "#e6f6cf", alignItems: "center", justifyContent: "center" },
  tileWarn: { backgroundColor: "#ffe6b3" },
  tileText: { fontSize: 18, fontWeight: "700", color: "#0f5c2e" },
  rowLabel: { fontSize: 15, fontWeight: "600", color: "#0d2b15" },
  rowWhy: { fontSize: 12, color: "#5b6b5e", marginTop: 2 },
  chip: { fontSize: 15, fontWeight: "700", color: "#0f5c2e", fontVariant: ["tabular-nums"] },
  chev: { fontSize: 22, color: "#9aa79c" },
  after: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", borderWidth: 2, borderColor: "#2c7a3a", borderRadius: 14, padding: 12 },
  afterLabel: { fontSize: 13, color: "#5b6b5e" }, afterValue: { fontSize: 22, fontWeight: "700", color: "#2c7a3a", fontVariant: ["tabular-nums"] },
  disclosure: { fontSize: 11, color: "#8a978c", lineHeight: 15 },
});
