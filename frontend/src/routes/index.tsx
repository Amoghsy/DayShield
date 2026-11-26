import { createFileRoute } from "@tanstack/react-router";
import { DayShieldDashboard } from "../components/DayShieldDashboard";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "DayShield | Disruption response desk" },
      {
        name: "description",
        content: "Coordinate commute disruption recovery with a transparent, human-approved DayShield response plan.",
      },
      { property: "og:title", content: "DayShield | Disruption response desk" },
      {
        property: "og:description",
        content: "A real-time disruption response desk with clear recovery options and explicit user approval.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: DayShieldDashboard,
});
