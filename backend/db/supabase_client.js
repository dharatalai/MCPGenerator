import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'
import path from 'path'

// Load environment variables
dotenv.config({ path: path.resolve(process.cwd(), '.env') })

// Supabase credentials from environment variables
const SUPABASE_URL = process.env.SUPABASE_URL
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  console.error('Missing Supabase credentials. Please check your .env file.')
  process.exit(1)
}

// Create Supabase client
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// Create admin client with service key for admin operations
const supabaseAdmin = SUPABASE_SERVICE_KEY 
  ? createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY)
  : null

// Template table operations
export const templateOperations = {
  // Create a new template
  async createTemplate(templateData) {
    const { data, error } = await supabase
      .from('templates')
      .insert(templateData)
      .select()
      .single()
    
    if (error) throw error
    return data
  },
  
  // Get a template by ID
  async getTemplateById(id) {
    const { data, error } = await supabase
      .from('templates')
      .select('*')
      .eq('id', id)
      .single()
    
    if (error) throw error
    return data
  },

  // Get all templates
  async getAllTemplates() {
    const { data, error } = await supabase
      .from('templates')
      .select('*')
    
    if (error) throw error
    return data
  }
}

// Server table operations
export const serverOperations = {
  // Create a new MCP server
  async createServer(serverData) {
    const { data, error } = await supabase
      .from('mcp_servers')
      .insert(serverData)
      .select()
      .single()
    
    if (error) throw error
    return data
  },
  
  // Get a server by ID
  async getServerById(id) {
    const { data, error } = await supabase
      .from('mcp_servers')
      .select('*')
      .eq('id', id)
      .single()
    
    if (error) throw error
    return data
  },
  
  // Update a server
  async updateServer(id, updates) {
    const { data, error } = await supabase
      .from('mcp_servers')
      .update(updates)
      .eq('id', id)
      .select()
      .single()
    
    if (error) throw error
    return data
  }
}

// User operations
export const userOperations = {
  // Get user by ID
  async getUserById(id) {
    const { data, error } = await supabase.auth.admin.getUserById(id)
    
    if (error) throw error
    return data.user
  },
  
  // Create new user
  async createUser(userData) {
    if (!supabaseAdmin) {
      throw new Error('Service role key is required for admin operations')
    }
    
    const { data, error } = await supabaseAdmin.auth.admin.createUser(userData)
    
    if (error) throw error
    return data.user
  }
}

export default supabase 