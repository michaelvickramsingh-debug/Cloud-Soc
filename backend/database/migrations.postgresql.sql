ALTER TABLE attack_scenarios
    ADD COLUMN IF NOT EXISTS attack_vector TEXT NOT NULL DEFAULT '';

ALTER TABLE attack_scenarios
    ADD COLUMN IF NOT EXISTS layer_targeted TEXT NOT NULL DEFAULT '';

ALTER TABLE attack_scenarios
    ADD COLUMN IF NOT EXISTS best_practice_violated TEXT NOT NULL DEFAULT '';

ALTER TABLE attack_scenarios
    ADD COLUMN IF NOT EXISTS mitre_tactics TEXT NOT NULL DEFAULT '';
