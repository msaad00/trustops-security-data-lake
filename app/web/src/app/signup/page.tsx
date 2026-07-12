import { redirect } from "next/navigation";

/** Self-serve signup is not surfaced in the OSS console — use local demo or SSO login. */
export default function SignupPage() {
  redirect("/login");
}
