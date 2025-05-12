import { useEffect } from "react";
import type { Route } from "./+types/home";
import { greet } from "@interface/index";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "New React Router App" },
    { name: "description", content: "Welcome to React Router!" },
  ];
}

export default function Home() {
  return <div>Hello World</div>;
}
