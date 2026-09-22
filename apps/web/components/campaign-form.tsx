"use client";

import { useState } from "react";

type CampaignFormProps = {
  busy: boolean;
  onCreate: (values: { name: string; location: string; sector: string; maximum: number }) => Promise<void>;
};

export function CampaignForm({ busy, onCreate }: CampaignFormProps) {
  const [name, setName] = useState("Dubai Dental Opportunity Scan");
  const [location, setLocation] = useState("Dubai Marina, Dubai, UAE");
  const [sector, setSector] = useState("dental clinic");
  const [maximum, setMaximum] = useState(10);

  return (
    <form
      className="campaign-form"
      onSubmit={(event) => {
        event.preventDefault();
        void onCreate({ name, location, sector, maximum });
      }}
    >
      <label className="field-name">
        <span><b>01</b> Campaign name</span>
        <input value={name} onChange={(event) => setName(event.target.value)} required placeholder="Name this research run" />
      </label>
      <label className="field-market">
        <span><b>02</b> Target market</span>
        <input value={location} onChange={(event) => setLocation(event.target.value)} required placeholder="City, region, country" />
      </label>
      <label className="field-sector">
        <span><b>03</b> Business category</span>
        <input value={sector} onChange={(event) => setSector(event.target.value)} required placeholder="e.g. dental clinics" />
      </label>
      <label className="field-maximum">
        <span><b>04</b> Search limit</span>
        <input
          type="number"
          min={1}
          max={250}
          value={maximum}
          onChange={(event) => setMaximum(Number(event.target.value))}
          required
        />
      </label>
      <div className="form-submit"><p>Only real matches can be returned. A limit is a ceiling, not a guaranteed count.</p><button className="primary-button" disabled={busy} type="submit">{busy ? "Researching…" : "Start research"}<span aria-hidden="true">↗</span></button></div>
    </form>
  );
}
