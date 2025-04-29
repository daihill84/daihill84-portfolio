import { MongoClient } from 'mongodb';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method not allowed' });
  }

  const { name, email, message } = req.body;

  if (!name || !email || !message) {
    return res.status(400).json({ message: 'All fields are required' });
  }

  const uri = process.env.MONGODB_URI; // Set in environment variables
  const client = new MongoClient(uri);

  try {
    await client.connect();
    const database = client.db('welshmolecatcher');
    const leads = database.collection('leads');

    const lead = {
      name,
      email,
      message,
      timestamp: new Date(),
    };

    await leads.insertOne(lead);
    res.status(200).json({ message: 'Lead submitted successfully' });
  } catch (error) {
    console.error('Error saving lead:', error);
    res.status(500).json({ message: 'Internal server error' });
  } finally {
    await client.close();
  }
}