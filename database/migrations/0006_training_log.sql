CREATE TABLE IF NOT EXISTS ml_training_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  classifier TEXT NOT NULL,
  input_json JSONB NOT NULL,
  prediction TEXT NOT NULL,
  confidence FLOAT NOT NULL,
  model_type TEXT NOT NULL,
  label TEXT,
  labeled_at TIMESTAMPTZ,
  labeled_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ml_training_log_classifier_idx ON ml_training_log(classifier, label);
CREATE INDEX IF NOT EXISTS ml_training_log_unlabeled_idx ON ml_training_log(classifier) WHERE label IS NULL;
