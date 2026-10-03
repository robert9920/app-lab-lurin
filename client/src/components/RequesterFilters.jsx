import SearchSelect from "./SearchSelect";
import { Field } from "./ui";

export default function RequesterFilters({ params, filter, view }) {
  return (
    <>
      {[
        ["requester", "Solicitante"],
        ["organization", "Empresa"],
      ].map(([key, label]) => (
        <Field key={key} label={label}>
          <SearchSelect
            value={params.get(key) || ""}
            onChange={(value) => filter(key, value)}
            remote={`/filter-options?view=${view}&kind=${key}`}
          />
        </Field>
      ))}
    </>
  );
}
