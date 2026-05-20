"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/services/api";

export function CampaignForm() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [keywords, setKeywords] = useState("pcos, stress, sleep, help, details");
  const [products, setProducts] = useState("Mind Calm, PCOS Support");
  const [whatsapp, setWhatsapp] = useState(true);

  const mutation = useMutation({
    mutationFn: () =>
      api.createCampaign({
        name,
        status: "active",
        keyword_triggers: keywords.split(",").map((k) => k.trim()).filter(Boolean),
        product_focus: products.split(",").map((p) => p.trim()).filter(Boolean),
        public_reply_enabled: true,
        dm_enabled: true,
        whatsapp_followup_enabled: whatsapp
      }),
    onSuccess: async () => {
      setName("");
      await queryClient.invalidateQueries({ queryKey: ["campaigns"] });
    }
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create Campaign</CardTitle>
      </CardHeader>
      <CardContent>
        <form className="grid gap-3 md:grid-cols-2" onSubmit={onSubmit}>
          <Input placeholder="Campaign name" value={name} onChange={(e) => setName(e.target.value)} required />
          <Input placeholder="Keywords (comma-separated)" value={keywords} onChange={(e) => setKeywords(e.target.value)} />
          <Input placeholder="Product focus (comma-separated)" value={products} onChange={(e) => setProducts(e.target.value)} />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={whatsapp} onChange={(e) => setWhatsapp(e.target.checked)} />
            WhatsApp follow-up enabled
          </label>
          <Button type="submit" disabled={mutation.isPending} className="md:col-span-2">
            {mutation.isPending ? "Creating…" : "Create campaign"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
