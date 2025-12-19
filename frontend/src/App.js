import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./App.css";

// Backend URL load karein
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:8000";
const API = `${BACKEND_URL}/api`;

// 👇 HELPER: Image URL ko sahi format me badalne ke liye
const getFullImageUrl = (url) => {
  if (!url) return null;
  // Agar pehle se http/https hai (jaise Pollinations URL), to waisa hi return karo
  if (url.startsWith("http") || url.startsWith("data:")) return url;
  // Agar local path hai (uploads/...), to Backend URL jodo
  return `${BACKEND_URL}/${url}`;
};

// Generate or retrieve user ID
const getUserId = () => {
  let userId = localStorage.getItem("luna_user_id");
  if (!userId) {
    userId = `user_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem("luna_user_id", userId);
  }
  return userId;
};

function App() {
  const [activeTab, setActiveTab] = useState("chat");
  const [userId] = useState(getUserId());
  
  // Chat state
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  
  // Image Analysis state
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [imageAnalysis, setImageAnalysis] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  
  // Gallery state
  const [galleryImages, setGalleryImages] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoadingGallery, setIsLoadingGallery] = useState(false);
  
  // Generated Images state
  const [generatedImages, setGeneratedImages] = useState([]);
  const [generationPrompt, setGenerationPrompt] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  
  const chatContainerRef = useRef(null);
  const fileInputRef = useRef(null);

  // Load chat history on mount
  useEffect(() => {
    loadChatHistory();
    // eslint-disable-next-line
  }, []);

  // Auto scroll chat
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // Load gallery when tab changes
  useEffect(() => {
    if (activeTab === "gallery") {
      loadGallery();
    } else if (activeTab === "generated") {
      loadGeneratedImages();
    }
    // eslint-disable-next-line
  }, [activeTab]);

  const loadChatHistory = async () => {
    try {
      const response = await axios.get(`${API}/history/${userId}`);
      const history = response.data;
      
      const formattedMessages = history.map(msg => ({
        role: msg.role === "assistant" ? "luna" : "user",
        content: msg.content,
        photo: msg.photo_sent || msg.image_url
      }));
      
      setMessages(formattedMessages);
    } catch (error) {
      console.error("Error loading history:", error);
    }
  };

  const loadGallery = async () => {
    setIsLoadingGallery(true);
    try {
      const response = await axios.get(`${API}/gallery/${userId}`, {
        params: searchQuery ? { search: searchQuery } : {}
      });
      setGalleryImages(response.data);
    } catch (error) {
      console.error("Error loading gallery:", error);
    } finally {
      setIsLoadingGallery(false);
    }
  };

  const loadGeneratedImages = async () => {
    try {
      const response = await axios.get(`${API}/generated-images/${userId}`);
      setGeneratedImages(response.data);
    } catch (error) {
      console.error("Error loading generated images:", error);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() && !selectedImage) return;

    const userMessage = inputMessage;
    setInputMessage("");
    
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      let imageAnalysisData = null;

      if (selectedImage) {
        const formData = new FormData();
        formData.append("user_id", userId);
        formData.append("file", selectedImage);

        const visionResponse = await axios.post(`${API}/analyze-image`, formData, {
          headers: { "Content-Type": "multipart/form-data" }
        });

        imageAnalysisData = visionResponse.data.analysis;
        setSelectedImage(null);
        setImagePreview(null);
      }

      const chatResponse = await axios.post(`${API}/chat`, {
        user_id: userId,
        message: userMessage,
        imageAnalysis: imageAnalysisData
      });

      setMessages(prev => [...prev, {
        role: "luna",
        content: chatResponse.data.reply,
        photo: chatResponse.data.photo_url
      }]);

    } catch (error) {
      console.error("Chat error:", error);
      setMessages(prev => [...prev, {
        role: "luna",
        content: "I'm having trouble connecting right now. Please try again."
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleImageSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedImage(file);
      const reader = new FileReader();
      reader.onload = (e) => setImagePreview(e.target.result);
      reader.readAsDataURL(file);
    }
  };

  const handleImageAnalysis = async () => {
    if (!selectedImage) return;

    setIsAnalyzing(true);
    try {
      const formData = new FormData();
      formData.append("user_id", userId);
      formData.append("file", selectedImage);

      const response = await axios.post(`${API}/analyze-image`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      setImageAnalysis(response.data.analysis);
    } catch (error) {
      console.error("Analysis error:", error);
      alert("Failed to analyze image");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleGenerateImage = async () => {
    if (!generationPrompt.trim()) return;

    setIsGenerating(true);
    try {
      const response = await axios.post(`${API}/generate-luna`, {
        user_id: userId,
        prompt: generationPrompt
      });

      // Nayi image ko list me sabse upar jodein
      setGeneratedImages(prev => [response.data, ...prev]);
      setGenerationPrompt("");
    } catch (error) {
      console.error("Generation error:", error);
      alert("Failed to generate image");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSearchGallery = (e) => {
    e.preventDefault();
    loadGallery();
  };

  return (
    <div className="App min-h-screen bg-slate-950 text-white font-sans">
      {/* Header */}
      <header className="bg-slate-900/50 backdrop-blur-lg border-b border-slate-800 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-r from-violet-600 to-indigo-600 p-0.5">
              <div className="w-full h-full rounded-full bg-slate-950 flex items-center justify-center">
                <span className="text-xl">🌕</span>
              </div>
            </div>
            <div>
              <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-violet-400 to-indigo-400">
                Luna AI
              </h1>
              <p className="text-xs text-slate-400">Cosmic Companion</p>
            </div>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="container mx-auto px-4 mt-6">
        <div className="flex gap-2 bg-slate-900/50 p-1 rounded-xl border border-slate-800 overflow-x-auto">
          {["chat", "analysis", "gallery", "generated"].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all capitalize whitespace-nowrap ${
                activeTab === tab
                  ? "bg-violet-600 text-white shadow-lg shadow-violet-500/20"
                  : "text-slate-400 hover:text-white hover:bg-slate-800"
              }`}
            >
              {tab === "chat" && "💬 Chat"}
              {tab === "analysis" && "🔍 Vision"}
              {tab === "gallery" && "🖼️ Gallery"}
              {tab === "generated" && "✨ Create"}
            </button>
          ))}
        </div>
      </div>

      {/* Content Area */}
      <div className="container mx-auto px-4 py-6 mb-20">
        {/* CHAT TAB */}
        {activeTab === "chat" && (
          <div className="max-w-3xl mx-auto h-[calc(100vh-220px)] flex flex-col">
            <div 
              ref={chatContainerRef}
              className="flex-1 overflow-y-auto space-y-6 pr-2 pb-4 scroll-smooth"
            >
              {messages.length === 0 && (
                <div className="text-center text-slate-500 mt-20">
                  <p className="text-4xl mb-4">👋</p>
                  <p>Say hello to Luna!</p>
                </div>
              )}
              
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
                >
                  <div className={`w-8 h-8 rounded-full shrink-0 flex items-center justify-center text-sm ${
                    msg.role === "user" 
                      ? "bg-slate-700 text-slate-200" 
                      : "bg-violet-600 text-white"
                  }`}>
                    {msg.role === "user" ? "U" : "L"}
                  </div>
                  
                  <div className={`max-w-[80%] space-y-2`}>
                    <div className={`p-4 rounded-2xl ${
                      msg.role === "user"
                        ? "bg-slate-800 text-slate-100 rounded-tr-none"
                        : "bg-violet-900/30 border border-violet-500/20 text-slate-100 rounded-tl-none"
                    }`}>
                      {msg.photo && (
                        <img 
                          src={getFullImageUrl(msg.photo)} 
                          alt="Shared" 
                          className="rounded-lg mb-3 w-full max-w-sm border border-slate-700"
                        />
                      )}
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  </div>
                </div>
              ))}
              
              {isLoading && (
                <div className="flex gap-4">
                  <div className="w-8 h-8 rounded-full bg-violet-600 flex items-center justify-center text-sm">L</div>
                  <div className="bg-violet-900/30 border border-violet-500/20 p-4 rounded-2xl rounded-tl-none">
                    <div className="flex gap-1.5">
                      <div className="w-2 h-2 bg-violet-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-violet-400 rounded-full animate-bounce delay-100"></div>
                      <div className="w-2 h-2 bg-violet-400 rounded-full animate-bounce delay-200"></div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Input Area */}
            <div className="mt-4">
              {imagePreview && (
                <div className="mb-3 relative inline-block">
                  <img src={imagePreview} alt="Preview" className="h-20 rounded-lg border border-slate-700" />
                  <button
                    onClick={() => {
                      setSelectedImage(null);
                      setImagePreview(null);
                    }}
                    className="absolute -top-2 -right-2 bg-red-500 text-white w-5 h-5 rounded-full flex items-center justify-center text-xs hover:bg-red-600"
                  >
                    ×
                  </button>
                </div>
              )}

              <form onSubmit={handleSendMessage} className="flex gap-2 relative">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleImageSelect}
                  accept="image/*"
                  className="hidden"
                />
                
                <div className="relative flex-1">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    placeholder="Message Luna..."
                    className="w-full bg-slate-900 border border-slate-800 rounded-full pl-12 pr-12 py-3 focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500 transition-all placeholder-slate-500"
                  />
                  
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="absolute left-3 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center rounded-full text-slate-400 hover:text-violet-400 hover:bg-slate-800 transition"
                  >
                    📷
                  </button>

                  <button
                    type="submit"
                    disabled={isLoading || (!inputMessage.trim() && !selectedImage)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 w-9 h-9 bg-violet-600 rounded-full flex items-center justify-center text-white hover:bg-violet-500 disabled:opacity-50 disabled:hover:bg-violet-600 transition shadow-lg shadow-violet-900/20"
                  >
                    ➤
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* IMAGE ANALYSIS TAB - UPDATED UI */}
        {activeTab === "analysis" && (
          <div className="max-w-3xl mx-auto">
            {!imagePreview ? (
              <div 
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-slate-700 rounded-2xl p-12 text-center cursor-pointer hover:border-violet-500 hover:bg-slate-900/50 transition-all group"
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleImageSelect}
                  accept="image/*"
                  className="hidden"
                />
                <div className="text-6xl mb-4 group-hover:scale-110 transition-transform">📸</div>
                <h3 className="text-xl font-semibold mb-2">Upload Image</h3>
                <p className="text-slate-400">Click to upload an image for detailed AI analysis</p>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="flex flex-col items-center">
                  <img 
                    src={imagePreview} 
                    alt="Selected" 
                    className="max-h-[400px] rounded-xl border border-slate-700 shadow-2xl"
                  />
                  
                  <div className="flex gap-3 mt-6">
                    <button
                      onClick={handleImageAnalysis}
                      disabled={isAnalyzing}
                      className="px-8 py-3 bg-violet-600 rounded-full font-semibold hover:bg-violet-500 transition disabled:opacity-50 shadow-lg shadow-violet-900/20"
                    >
                      {isAnalyzing ? "Analyzing..." : "🔍 Ask Luna"}
                    </button>
                    <button
                      onClick={() => {
                        setSelectedImage(null);
                        setImagePreview(null);
                        setImageAnalysis(null);
                      }}
                      className="px-8 py-3 bg-slate-800 rounded-full font-semibold hover:bg-slate-700 transition"
                    >
                      Clear
                    </button>
                  </div>
                </div>

                {imageAnalysis && (
                  <div className="mt-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    
                    {/* 👇 NEW: Luna's Direct Comment (Hero Section) */}
                    <div className="bg-gradient-to-r from-violet-900/50 to-indigo-900/50 p-6 rounded-2xl border border-violet-500/30 text-center mb-6">
                      <div className="text-4xl mb-2">✨</div>
                      {/* Luna's Interactive Comment */}
                      <h3 className="text-xl md:text-2xl font-bold text-white leading-relaxed">
                        "{imageAnalysis.comment || "Wow, interesting shot!"}"
                      </h3>
                      <p className="text-violet-300 text-sm mt-2">- Luna's Reaction</p>
                    </div>

                    {/* Technical Details (Smaller and below) */}
                    <div className="grid grid-cols-2 gap-4 text-xs md:text-sm">
                      <div className="bg-slate-900 p-4 rounded-xl border border-slate-800">
                        <h3 className="font-bold text-slate-500 mb-1 uppercase">Mood</h3>
                        <p className="text-slate-200 capitalize">{imageAnalysis.mood}</p>
                      </div>
                      
                      <div className="bg-slate-900 p-4 rounded-xl border border-slate-800">
                        <h3 className="font-bold text-slate-500 mb-1 uppercase">Score</h3>
                        <p className="text-green-400 font-bold">{imageAnalysis.safety_score}% Safe</p>
                      </div>

                      <div className="bg-slate-900 p-4 rounded-xl border border-slate-800 col-span-2">
                         <h3 className="font-bold text-slate-500 mb-2 uppercase">Detected Objects</h3>
                         <div className="flex flex-wrap gap-2">
                            {imageAnalysis.objects?.map((obj, idx) => (
                              <span key={idx} className="px-2 py-1 bg-slate-800 border border-slate-700 rounded-full text-slate-400">
                                {obj}
                              </span>
                            ))}
                         </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* GALLERY TAB */}
        {activeTab === "gallery" && (
          <div className="max-w-6xl mx-auto">
            <form onSubmit={handleSearchGallery} className="mb-8">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search visual memories..."
                  className="flex-1 px-5 py-3 bg-slate-900 border border-slate-800 rounded-xl focus:outline-none focus:border-violet-500 transition-colors"
                />
                <button
                  type="submit"
                  className="px-6 py-3 bg-slate-800 rounded-xl font-semibold hover:bg-slate-700 transition"
                >
                  🔍
                </button>
              </div>
            </form>

            {isLoadingGallery ? (
              <div className="text-center py-20 text-slate-500">Loading memories...</div>
            ) : galleryImages.length === 0 ? (
              <div className="text-center py-20 text-slate-500">
                <p className="text-4xl mb-4">🖼️</p>
                <p>No images found.</p>
              </div>
            ) : (
              <div className="columns-1 md:columns-2 lg:columns-3 gap-4 space-y-4">
                {galleryImages.map((img, idx) => (
                  <div key={idx} className="break-inside-avoid bg-slate-900 rounded-xl overflow-hidden border border-slate-800 hover:border-violet-500/50 transition group">
                    {img.image_url && (
                      <img 
                        src={getFullImageUrl(img.image_url)} 
                        alt={img.description}
                        className="w-full object-cover group-hover:scale-105 transition-transform duration-500"
                        loading="lazy"
                      />
                    )}
                    <div className="p-4">
                      <p className="text-sm text-slate-300 mb-3 line-clamp-2">{img.description}</p>
                      <div className="flex flex-wrap gap-1.5">
                        {img.tags?.slice(0, 3).map((tag, tidx) => (
                          <span key={tidx} className="px-2 py-0.5 bg-slate-800 rounded-full text-[10px] text-slate-400 border border-slate-700">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* GENERATED IMAGES TAB */}
        {activeTab === "generated" && (
          <div className="max-w-6xl mx-auto">
            <div className="mb-8 bg-slate-900 p-6 rounded-2xl border border-slate-800">
              <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                <span className="text-violet-400">✨</span> Dream & Create
              </h2>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={generationPrompt}
                  onChange={(e) => setGenerationPrompt(e.target.value)}
                  placeholder="Imagine something cosmic..."
                  className="flex-1 px-5 py-3 bg-slate-950 border border-slate-800 rounded-xl focus:outline-none focus:border-violet-500 transition-colors"
                />
                <button
                  onClick={handleGenerateImage}
                  disabled={isGenerating}
                  className="px-6 py-3 bg-violet-600 rounded-xl font-semibold hover:bg-violet-500 transition disabled:opacity-50"
                >
                  {isGenerating ? "Creating..." : "Generate"}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="generated-grid">
              {generatedImages.map((img, idx) => (
                <div key={idx} className="bg-slate-900 rounded-xl overflow-hidden border border-slate-800 relative group">
                  <div className="absolute inset-0 bg-slate-800 animate-pulse -z-10"></div>
                  <img 
                    src={getFullImageUrl(img.image_url || img.imageUrl)} 
                    alt={img.prompt}
                    className="w-full h-64 object-cover transition-transform duration-700 group-hover:scale-105"
                    referrerPolicy="no-referrer"
                    onError={(e) => {
                      e.target.onerror = null; 
                      e.target.src = "https://placehold.co/800x600/1e293b/FFF?text=Image+Expired";
                    }}
                  />
                  <div className="p-4 bg-gradient-to-t from-slate-950 to-transparent">
                    <p className="text-sm font-medium text-violet-200 mb-1 line-clamp-1">{img.caption}</p>
                    <p className="text-xs text-slate-400">"{img.prompt}"</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;