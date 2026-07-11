import { redirect } from "next/navigation";

/** Pricing is not surfaced in the OSS console — deployment options live on /deploy. */
export default function PricingPage() {
  redirect("/deploy");
}
