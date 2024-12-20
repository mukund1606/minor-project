import 'dotenv/config';

import { readFileSync, unlinkSync } from 'fs';

import multer from 'multer';

import { Router } from 'express';

import jwt from 'jsonwebtoken';

import UserModel from '../db/models/userModel.js';

const userRouter = Router();

const JWT_SECRET = process.env.JWT_SECRET;

const upload = multer({
	dest: 'public/',
});

userRouter.post('/signup', upload.single('image'), async (req, res) => {
	try {
		const data = req.body;
		const name = data?.name;
		const username = data?.username;
		const password = data?.password;
		const imageData = req.file;

		if (!name) {
			return res.status(400).json({ message: 'Name is required!' });
		} else if (!username) {
			return res.status(400).json({ message: 'Username is required!' });
		} else if (!password) {
			return res.status(400).json({ message: 'Password is required!' });
		} else if (!imageData) {
			return res.status(400).json({ message: 'Image is required!' });
		}

		const existingUser = await UserModel.findOne({
			username: username,
		});

		if (existingUser) {
			return res.status(400).json({ message: 'Username already exists!' });
		}

		const file = readFileSync(imageData.path);
		unlinkSync(imageData.path);

		const newUser = new UserModel({
			name: name,
			username: username,
			passwordHash: password,
			image: file,
		});

		const hashedPassword = await newUser.createHash(password);
		newUser.passwordHash = hashedPassword;

		await newUser.save();

		const userId = newUser._id;

		const token = jwt.sign({ userId }, JWT_SECRET);

		res.cookie('token', token, {
			secure: true,
			httpOnly: true,
			sameSite: 'none',
		});
		res.json({ message: 'User created successfully!' });
	} catch (error) {
		console.error(error);
		res.status(500).json({ message: 'Internal server error!' });
	}
});

userRouter.post('/login', async (req, res) => {
	try {
		const data = req.body;
		const username = data?.username;
		const password = data?.password;

		if (!username) {
			return res.status(400).json({ message: 'Username is required!' });
		} else if (!password) {
			return res.status(400).json({ message: 'Password is required!' });
		}

		const user = await UserModel.findOne({ username: username });

		if (!user) {
			return res.status(400).json({ message: 'User not found!' });
		}

		const isPasswordCorrect = await user.validatePassword(password);

		if (!isPasswordCorrect) {
			return res.status(400).json({ message: 'Incorrect password!' });
		}

		const token = jwt.sign({ userId: user._id }, JWT_SECRET);

		res.cookie('token', token, {
			secure: true,
			httpOnly: true,
			sameSite: 'none',
		});
		res.json({ message: 'Login successful!' });
	} catch (error) {
		console.error(error);
		res.status(500).json({ message: 'Internal server error!' });
	}
});

userRouter.post('/logout', async (req, res) => {
	res.clearCookie('token', {
		secure: true,
		httpOnly: true,
		sameSite: 'none',
	});
	res.json({ message: 'Logged out successfully!' });
});

userRouter.get('/', async (req, res) => {
	try {
		const token = req.cookies.token;
		if (!token) {
			return res.status(401).json({ message: 'Unauthorized!' });
		}
		const { userId } = jwt.verify(token, JWT_SECRET);
		const user = await UserModel.findById(userId);
		res.json({
			id: user._id,
			name: user.name,
			username: user.username,
			image: user.image,
			joinedDate: user.createdAt,
		});
	} catch (error) {
		console.error(error);
		res.status(500).json({ message: 'Internal server error!' });
	}
});

export default userRouter;
