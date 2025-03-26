-- Templates Table
CREATE TABLE templates (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  description TEXT,
  category TEXT,
  template_path TEXT,
  version TEXT,
  is_public BOOLEAN DEFAULT FALSE,
  config_schema JSONB DEFAULT '{}',
  created_by UUID,
  requires_approval BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE
);

-- MCP Servers Table
CREATE TABLE mcp_servers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  description TEXT,
  template_id UUID REFERENCES templates(id),
  user_id UUID NOT NULL,
  status TEXT DEFAULT 'created',
  deployment_url TEXT,
  config JSONB DEFAULT '{}',
  credentials JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE
);

-- Enable Row Level Security (RLS)
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE mcp_servers ENABLE ROW LEVEL SECURITY;

-- Policies for templates
CREATE POLICY "Allow public access to public templates" 
  ON templates FOR SELECT USING (is_public = TRUE);

CREATE POLICY "Allow users to access their own templates" 
  ON templates FOR ALL USING (created_by = auth.uid());

-- Policies for MCP servers
CREATE POLICY "Allow users to access their own servers" 
  ON mcp_servers FOR ALL USING (user_id = auth.uid());

-- Create function for updated_at trigger
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger to templates table
CREATE TRIGGER update_templates_updated_at
  BEFORE UPDATE ON templates
  FOR EACH ROW EXECUTE PROCEDURE update_modified_column();

-- Add trigger to mcp_servers table
CREATE TRIGGER update_mcp_servers_updated_at
  BEFORE UPDATE ON mcp_servers
  FOR EACH ROW EXECUTE PROCEDURE update_modified_column(); 