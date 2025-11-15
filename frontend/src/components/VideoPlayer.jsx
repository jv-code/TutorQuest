import { useState, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Volume2, VolumeX } from 'lucide-react'
import { Button } from './ui/button'

export function VideoPlayer({ videoUrl }) {
  const [isMuted, setIsMuted] = useState(false)
  const videoRef = useRef(null)

  if (!videoUrl) return null

  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted
      setIsMuted(!isMuted)
    }
  }

  return (
    <Card className="mb-4">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Video Explanation</CardTitle>
        <Button
          variant="outline"
          size="icon"
          onClick={toggleMute}
          className="h-8 w-8"
        >
          {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
        </Button>
      </CardHeader>
      <CardContent>
        <video ref={videoRef} controls className="w-full rounded-md" muted={false}>
          <source src={videoUrl} type="video/mp4" />
        </video>
      </CardContent>
    </Card>
  )
}
