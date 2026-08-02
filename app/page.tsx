import lensData from "../data/lenses.json";
import { LensLibrary } from "./LensLibrary";
import { loadPublishedLenses } from "./lens-data";

const publishedLenses = loadPublishedLenses(lensData);

export default function Home() {
  return <LensLibrary lenses={publishedLenses} />;
}
